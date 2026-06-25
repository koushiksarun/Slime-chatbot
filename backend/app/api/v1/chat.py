"""
Chat API — handles both streaming (SSE) and non-streaming responses.
Pipeline per request:
  1. Rate limit check
  2. Prompt injection detection
  3. Load/create conversation
  4. Retrieve memory context
  5. RAG retrieval (if enabled)
  6. LLM call (streaming or batch)
  7. Persist messages + update token counts
  8. Optionally trigger summarization
"""
import json
import time
import uuid
from typing import Optional, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import sanitize_input
from app.middleware.auth import get_current_user
from app.middleware.rate_limiter import rate_limit_middleware
from app.models.user import User
from app.models.conversation import Conversation, Message, MessageRole
from app.schemas.chat import (
    ChatRequest, ConversationResponse, ConversationDetail,
    MessageResponse, StreamChunk
)
from app.services.ai.llm_service import LLMService
from app.services.memory.memory_service import MemoryService
from app.services.rag.rag_service import RAGService
from app.services.agents.agent_service import AgentService

router = APIRouter(prefix="/chat", tags=["Chat"])


async def _get_or_create_conversation(
    conversation_id: Optional[uuid.UUID],
    user: User,
    db: AsyncSession,
) -> Conversation:
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conv

    conv = Conversation(user_id=user.id, model_used="pending")
    db.add(conv)
    await db.flush()
    return conv


async def _stream_response(
    user_message: str,
    conversation: Conversation,
    user: User,
    request: ChatRequest,
    db: AsyncSession,
) -> AsyncIterator[str]:
    """Generator for SSE streaming response."""
    memory_svc = MemoryService(db)
    llm_svc = LLMService()

    try:
        # Load history and memory
        history = await memory_svc.get_short_term_history(conversation.id)
        summary = await memory_svc.get_long_term_summary(conversation.id)
        profile = memory_svc.format_profile_for_prompt(user.profile_memory)

        # RAG retrieval
        rag_context = ""
        citations = []
        if request.use_rag:
            rag_svc = RAGService(db)
            try:
                rag_context, citations = await rag_svc.retrieve(
                    query=user_message,
                    user_id=user.id,
                    document_ids=request.document_ids,
                )
            except Exception:
                rag_context, citations = "", []

        # Send citations first so UI can render them immediately
        if citations:
            citation_chunk = StreamChunk(
                type="citation",
                citations=citations,
            )
            yield f"data: {citation_chunk.model_dump_json()}\n\n"

        # Stream LLM tokens
        full_response = []
        start_time = time.time()

        async for token in llm_svc.stream(
            user_message=user_message,
            history=history,
            rag_context=rag_context if rag_context else None,
            profile_memory=profile,
        ):
            full_response.append(token)
            chunk = StreamChunk(type="token", content=token)
            yield f"data: {chunk.model_dump_json()}\n\n"

        latency_ms = int((time.time() - start_time) * 1000)
        response_content = "".join(full_response)

        # Persist user message
        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=user_message,
        )
        db.add(user_msg)

        # Persist assistant message
        assistant_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_content,
            citations=[c.model_dump() for c in citations] if citations else None,
            latency_ms=latency_ms,
            model_used=llm_svc.provider,
        )
        db.add(assistant_msg)
        await db.flush()
        await db.refresh(assistant_msg)

        # Update conversation title (auto-generate from first message)
        if not conversation.title:
            short_title = user_message[:80] + ("..." if len(user_message) > 80 else "")
            conversation.title = short_title

        # Send done event with message ID
        done_chunk = StreamChunk(
            type="done",
            message_id=str(assistant_msg.id),
            conversation_id=str(conversation.id),
        )
        yield f"data: {done_chunk.model_dump_json()}\n\n"

        # Background: profile extraction and summarization
        await memory_svc.extract_and_update_profile(user.id, user_message)
        if await memory_svc.should_summarize(conversation.id):
            await memory_svc.generate_summary(conversation.id)

    except Exception as e:
        error_chunk = StreamChunk(type="error", error=str(e))
        yield f"data: {error_chunk.model_dump_json()}\n\n"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/")
@router.post("")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Rate limit
    await rate_limit_middleware(None, str(current_user.id))

    # Sanitize input (prompt injection check)
    clean_message = sanitize_input(request.message)

    # Get or create conversation
    conversation = await _get_or_create_conversation(
        request.conversation_id, current_user, db
    )

    if request.stream:
        return StreamingResponse(
            _stream_response(clean_message, conversation, current_user, request, db),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    # Non-streaming path
    memory_svc = MemoryService(db)
    llm_svc = LLMService()

    history = await memory_svc.get_short_term_history(conversation.id)
    profile = memory_svc.format_profile_for_prompt(current_user.profile_memory)

    rag_context = ""
    citations = []
    if request.use_rag:
        rag_svc = RAGService(db)
        try:
            rag_context, citations = await rag_svc.retrieve(
                query=clean_message,
                user_id=current_user.id,
                document_ids=request.document_ids,
            )
        except Exception:
            rag_context, citations = "", []

    if request.use_agents:
        agent_svc = AgentService()
        result = await agent_svc.run(clean_message, history)
        response_content = result["content"]
        tool_calls = result["tool_calls"]
        metadata = {"model_used": "agent", "latency_ms": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0}
    else:
        metadata = await llm_svc.generate(
            user_message=clean_message,
            history=history,
            rag_context=rag_context if rag_context else None,
            profile_memory=profile,
        )
        response_content = metadata.pop("content")
        tool_calls = None

    # Persist
    user_msg = Message(conversation_id=conversation.id, role=MessageRole.USER, content=clean_message)
    db.add(user_msg)

    assistant_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=response_content,
        citations=[c.model_dump() for c in citations] if citations else None,
        tool_calls=tool_calls,
        **metadata,
    )
    db.add(assistant_msg)
    await db.flush()
    await db.refresh(assistant_msg)

    if not conversation.title:
        conversation.title = clean_message[:80]

    return MessageResponse.model_validate(assistant_msg)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.is_archived == False)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    conversations = result.scalars().all()

    # Attach message count
    response = []
    for conv in conversations:
        count_result = await db.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        )
        conv_dict = ConversationResponse.model_validate(conv)
        conv_dict.message_count = count_result.scalar_one()
        response.append(conv_dict)

    return response


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = msgs_result.scalars().all()

    detail = ConversationDetail.model_validate(conv)
    detail.messages = [MessageResponse.model_validate(m) for m in messages]
    return detail


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
