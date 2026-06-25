"""
Document upload and management API.
File upload → background ingestion (extract + chunk + embed + store).
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.services.rag.rag_service import RAGService

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _validate_file(file: UploadFile) -> str:
    """Returns file extension or raises HTTPException."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )
    return ext


async def _ingest_in_background(document_id: uuid.UUID, db_url: str):
    """Run in background task — creates its own DB session."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    engine = create_async_engine(db_url)
    AsyncLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncLocal() as session:
        async with session.begin():
            rag_svc = RAGService(session)
            await rag_svc.ingest_document(document_id)


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    is_public: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = _validate_file(file)

    # Check file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Save file to disk
    safe_filename = f"{uuid.uuid4()}.{ext}"
    file_path = UPLOAD_DIR / safe_filename
    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = Document(
        user_id=current_user.id,
        filename=safe_filename,
        original_filename=file.filename,
        file_type=ext,
        file_size_bytes=len(content),
        file_path=str(file_path),
        is_public=is_public,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Queue background ingestion
    background_tasks.add_task(
        _ingest_in_background, doc.id, settings.DATABASE_URL
    )

    return DocumentResponse.model_validate(doc)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    docs = result.scalars().all()

    total_result = await db.execute(
        select(Document).where(Document.user_id == current_user.id)
    )
    total = len(total_result.scalars().all())

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    await db.delete(doc)
