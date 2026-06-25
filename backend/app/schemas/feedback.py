from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.feedback import FeedbackRating, FeedbackStatus


class FeedbackCreate(BaseModel):
    message_id: uuid.UUID
    rating: FeedbackRating
    comment: Optional[str] = Field(None, max_length=2000)


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    rating: FeedbackRating
    comment: Optional[str]
    status: FeedbackStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackReview(BaseModel):
    status: FeedbackStatus
    review_notes: Optional[str] = None


class FeedbackStats(BaseModel):
    total: int
    thumbs_up: int
    thumbs_down: int
    pending_review: int
    approved: int
    rejected: int
    approval_rate: float
