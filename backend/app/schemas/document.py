from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    status: DocumentStatus
    chunk_count: int
    is_public: bool
    created_at: datetime
    processed_at: Optional[datetime]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
