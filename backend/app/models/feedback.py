from datetime import datetime
from typing import Optional
import uuid
import enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class FeedbackRating(str, enum.Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


class FeedbackStatus(str, enum.Enum):
    PENDING = "pending"       # Awaiting human review
    APPROVED = "approved"     # Approved for fine-tuning dataset
    REJECTED = "rejected"     # Rejected (bad data quality)
    IN_DATASET = "in_dataset" # Already exported to training set


class Feedback(Base):
    """
    Stores user ratings on assistant responses.
    These feed the RLHF pipeline after human review.
    No automatic retraining — data flows through admin approval first.
    """
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    rating: Mapped[FeedbackRating] = mapped_column(String(20), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Snapshot of the prompt-response pair at time of feedback
    prompt_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Admin review fields
    status: Mapped[FeedbackStatus] = mapped_column(
        String(20), default=FeedbackStatus.PENDING, nullable=False, index=True
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="feedbacks")
    message: Mapped["Message"] = relationship("Message", back_populates="feedback")
