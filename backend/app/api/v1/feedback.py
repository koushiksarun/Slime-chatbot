from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.middleware.auth import get_current_user, get_current_admin
from app.models.feedback import Feedback, FeedbackStatus, FeedbackRating
from app.models.conversation import Message, MessageRole
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackResponse, FeedbackReview, FeedbackStats

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify message exists and belongs to user's conversation
    msg_result = await db.execute(
        select(Message).where(Message.id == payload.message_id)
    )
    message = msg_result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.role != MessageRole.ASSISTANT:
        raise HTTPException(status_code=400, detail="Feedback can only be given on assistant messages")

    # Check for existing feedback
    existing = await db.execute(
        select(Feedback).where(Feedback.message_id == payload.message_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Feedback already submitted for this message")

    # Fetch the preceding user message as prompt snapshot
    from app.models.conversation import Conversation
    conv_result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == message.conversation_id,
            Message.role == MessageRole.USER,
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    user_msg = conv_result.scalar_one_or_none()

    feedback = Feedback(
        user_id=current_user.id,
        message_id=payload.message_id,
        rating=payload.rating,
        comment=payload.comment,
        prompt_snapshot=user_msg.content if user_msg else None,
        response_snapshot=message.content,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)


@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    total = (await db.execute(select(func.count(Feedback.id)))).scalar_one()
    thumbs_up = (await db.execute(
        select(func.count(Feedback.id)).where(Feedback.rating == FeedbackRating.THUMBS_UP)
    )).scalar_one()
    thumbs_down = total - thumbs_up
    pending = (await db.execute(
        select(func.count(Feedback.id)).where(Feedback.status == FeedbackStatus.PENDING)
    )).scalar_one()
    approved = (await db.execute(
        select(func.count(Feedback.id)).where(Feedback.status == FeedbackStatus.APPROVED)
    )).scalar_one()
    rejected = (await db.execute(
        select(func.count(Feedback.id)).where(Feedback.status == FeedbackStatus.REJECTED)
    )).scalar_one()

    return FeedbackStats(
        total=total,
        thumbs_up=thumbs_up,
        thumbs_down=thumbs_down,
        pending_review=pending,
        approved=approved,
        rejected=rejected,
        approval_rate=round(approved / total * 100, 1) if total > 0 else 0.0,
    )


@router.get("/pending", response_model=list[FeedbackResponse])
async def list_pending_feedback(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Feedback)
        .where(Feedback.status == FeedbackStatus.PENDING)
        .order_by(Feedback.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    return [FeedbackResponse.model_validate(f) for f in result.scalars().all()]


@router.patch("/{feedback_id}/review", response_model=FeedbackResponse)
async def review_feedback(
    feedback_id: uuid.UUID,
    payload: FeedbackReview,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    feedback = result.scalar_one_or_none()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    feedback.status = payload.status
    feedback.reviewed_by = current_admin.email
    feedback.reviewed_at = datetime.now(timezone.utc)
    feedback.review_notes = payload.review_notes
    await db.flush()
    await db.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)
