"""
Admin dashboard API — metrics, user management, conversation analytics.
All endpoints require ADMIN or MODERATOR role.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List
import uuid

from app.core.database import get_db
from app.middleware.auth import get_current_admin, get_current_superadmin
from app.models.user import User, UserRole
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.feedback import Feedback, FeedbackRating
from app.schemas.user import UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/metrics")
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Dashboard summary metrics."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    active_users = (await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )).scalar_one()
    total_conversations = (await db.execute(select(func.count(Conversation.id)))).scalar_one()
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar_one()
    total_documents = (await db.execute(select(func.count(Document.id)))).scalar_one()

    # Token usage and cost
    cost_result = await db.execute(select(func.sum(Conversation.total_cost_usd)))
    total_cost = float(cost_result.scalar_one() or 0)

    tokens_result = await db.execute(select(func.sum(Conversation.total_tokens)))
    total_tokens = int(tokens_result.scalar_one() or 0)

    # Feedback stats
    total_feedback = (await db.execute(select(func.count(Feedback.id)))).scalar_one()
    positive_feedback = (await db.execute(
        select(func.count(Feedback.id)).where(Feedback.rating == FeedbackRating.THUMBS_UP)
    )).scalar_one()

    return {
        "users": {
            "total": total_users,
            "active": active_users,
        },
        "conversations": {
            "total": total_conversations,
            "total_messages": total_messages,
        },
        "documents": {
            "total": total_documents,
        },
        "ai_usage": {
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
        },
        "feedback": {
            "total": total_feedback,
            "positive": positive_feedback,
            "satisfaction_rate": round(positive_feedback / total_feedback * 100, 1) if total_feedback > 0 else 0,
        },
    }


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(User)
        .order_by(desc(User.created_at))
        .offset(offset)
        .limit(per_page)
    )
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.patch("/users/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_user_active(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superadmin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: uuid.UUID,
    role: UserRole,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superadmin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/conversations")
async def list_all_conversations(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Conversation, User.email, User.username)
        .join(User, Conversation.user_id == User.id)
        .order_by(desc(Conversation.updated_at))
        .offset(offset)
        .limit(per_page)
    )
    rows = result.all()
    return [
        {
            "id": str(conv.id),
            "title": conv.title,
            "user_email": email,
            "username": username,
            "total_tokens": conv.total_tokens,
            "total_cost_usd": conv.total_cost_usd,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
        }
        for conv, email, username in rows
    ]


@router.get("/model-performance")
async def model_performance(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Average latency and cost per model."""
    result = await db.execute(
        select(
            Message.model_used,
            func.avg(Message.latency_ms).label("avg_latency_ms"),
            func.avg(Message.cost_usd).label("avg_cost_usd"),
            func.count(Message.id).label("message_count"),
        )
        .where(Message.model_used.isnot(None))
        .group_by(Message.model_used)
    )
    return [
        {
            "model": row.model_used,
            "avg_latency_ms": round(float(row.avg_latency_ms or 0), 1),
            "avg_cost_usd": round(float(row.avg_cost_usd or 0), 6),
            "message_count": row.message_count,
        }
        for row in result.all()
    ]
