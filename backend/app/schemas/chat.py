from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
import uuid

from app.models.conversation import MessageRole


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[uuid.UUID] = None
    use_rag: bool = True
    use_agents: bool = False
    document_ids: Optional[List[uuid.UUID]] = None  # Scope RAG to specific docs
    stream: bool = True


class Citation(BaseModel):
    document_id: str
    document_name: str
    chunk_text: str
    page_number: Optional[int] = None
    score: float


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: MessageRole
    content: str
    citations: Optional[List[Citation]] = None
    tool_calls: Optional[List[dict]] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    model_used: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    summary: Optional[str]
    model_used: Optional[str]
    total_tokens: int
    total_cost_usd: float
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationResponse):
    messages: List[MessageResponse] = []


class StreamChunk(BaseModel):
    """Sent as SSE data during streaming."""
    type: str  # "token" | "citation" | "tool_call" | "done" | "error"
    content: Optional[str] = None
    citations: Optional[List[Citation]] = None
    tool_name: Optional[str] = None
    tool_result: Optional[Any] = None
    message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    error: Optional[str] = None
