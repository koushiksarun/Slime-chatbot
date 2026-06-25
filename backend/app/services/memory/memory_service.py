"""
Memory Service — two-tier memory architecture:
  1. Short-term: last N messages from DB (sliding window)
  2. Long-term: LLM-generated summaries stored in conversation.memory_context
  3. Profile: extracted user facts stored in user.profile_memory
"""
from typing import Optional, List
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from app.core.config import settings
from app.models.conversation import Conversation, Message, MessageRole


SUMMARIZE_PROMPT = """Summarize the following conversation into a concise paragraph
that captures the key topics, decisions, and context.
This summary will be used to give an AI assistant memory of past conversations.
Keep it under 300 words.

Conversation:
{conversation}

Summary:"""

PROFILE_EXTRACT_PROMPT = """Extract factual information about the user from this message that would be
useful to remember for future conversations (name, preferences, profession, goals, constraints, etc.).
Return as a JSON object. If nothing notable, return {{}}.

Message: {message}

JSON:"""


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_short_term_history(
        self,
        conversation_id,
        window_size: int = None,
    ) -> List[dict]:
        """Returns last N messages as a list of dicts for LLM context."""
        window = window_size or settings.CONVERSATION_WINDOW_SIZE

        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .where(Message.role.in_([MessageRole.USER, MessageRole.ASSISTANT]))
            .order_by(Message.created_at.desc())
            .limit(window)
        )
        messages = result.scalars().all()
        # Reverse to chronological order
        return [
            {"role": m.role, "content": m.content}
            for m in reversed(messages)
        ]

    async def get_long_term_summary(self, conversation_id) -> Optional[str]:
        """Returns the stored summary for a conversation."""
        result = await self.db.execute(
            select(Conversation.summary).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def should_summarize(self, conversation_id) -> bool:
        """Check if conversation is long enough to trigger summarization."""
        result = await self.db.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        )
        count = result.scalar_one()
        return count > 0 and count % settings.SUMMARIZE_AFTER_TURNS == 0

    async def generate_summary(self, conversation_id) -> str:
        """Generate and persist an LLM summary of the full conversation."""
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-your"):
            return ""

        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()

        conversation_text = "\n".join(
            f"{m.role.upper()}: {m.content[:500]}" for m in messages
        )

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3,
        )
        response = await llm.ainvoke([
            SystemMessage(content="You are a helpful summarizer."),
            HumanMessage(content=SUMMARIZE_PROMPT.format(conversation=conversation_text)),
        ])

        summary = response.content

        # Persist to DB
        await self.db.execute(
            Conversation.__table__.update()
            .where(Conversation.id == conversation_id)
            .values(summary=summary)
        )

        return summary

    async def extract_and_update_profile(self, user_id, message: str):
        """
        Extract facts from user message and merge into user.profile_memory.
        Only called on user messages — not every turn, only when informative.
        """
        # Simple heuristic: only run if message contains self-referential keywords
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-your"):
            return

        triggers = ["i am", "i'm", "my name", "i work", "i like", "i prefer", "i need", "i use"]
        if not any(t in message.lower() for t in triggers):
            return

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY,
            temperature=0.0,
        )
        response = await llm.ainvoke([
            HumanMessage(content=PROFILE_EXTRACT_PROMPT.format(message=message)),
        ])

        try:
            extracted = json.loads(response.content)
            if not extracted:
                return

            # Fetch and merge with existing profile
            from app.models.user import User
            from sqlalchemy import select as sa_select
            result = await self.db.execute(sa_select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return

            existing = json.loads(user.profile_memory) if user.profile_memory else {}
            existing.update(extracted)
            user.profile_memory = json.dumps(existing)

        except (json.JSONDecodeError, Exception):
            pass  # Silent fail — profile extraction is best-effort

    def format_profile_for_prompt(self, profile_json: Optional[str]) -> Optional[str]:
        if not profile_json:
            return None
        try:
            profile = json.loads(profile_json)
            if not profile:
                return None
            lines = [f"- {k}: {v}" for k, v in profile.items()]
            return "Known facts about this user:\n" + "\n".join(lines)
        except Exception:
            return None
