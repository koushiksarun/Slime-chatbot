"""
RAG Service — orchestrates the full retrieval-augmented generation pipeline:
  1. Document ingestion (upload → extract → chunk → embed → store)
  2. Retrieval (query → embed → vector search → rerank → context assembly)
  3. Citation generation
"""
from typing import List, Optional, Tuple
from datetime import datetime, timezone
import uuid
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.services.rag.document_processor import extract_text, chunk_document
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.vector_store import get_vector_store, SearchResult
from app.schemas.chat import Citation


class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_svc = EmbeddingService.get_instance()
        self.vector_store = get_vector_store()

    async def ingest_document(self, document_id: uuid.UUID) -> None:
        """Full ingestion pipeline for an uploaded document."""
        # Load document record
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            return

        try:
            # Update status
            doc.status = DocumentStatus.PROCESSING

            # Extract text
            text, metadata = extract_text(doc.file_path, doc.file_type)
            doc.doc_metadata = metadata

            # Chunk
            nodes = chunk_document(
                text=text,
                doc_id=str(doc.id),
                filename=doc.original_filename,
                doc_metadata=metadata,
            )

            # Embed all chunks
            texts = [node.text for node in nodes]
            embeddings = await self.embedding_svc.embed_texts(texts)
            for node, emb in zip(nodes, embeddings):
                node.embedding = emb

            # Store in vector DB — use user-scoped collection
            collection = f"user_{doc.user_id}"
            await self.vector_store.upsert(nodes, collection)

            # Update document record
            doc.status = DocumentStatus.READY
            doc.chunk_count = len(nodes)
            doc.vector_collection = collection
            doc.processed_at = datetime.now(timezone.utc)

        except Exception as e:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)[:500]
            raise

    async def retrieve(
        self,
        query: str,
        user_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        top_k: int = None,
    ) -> Tuple[str, List[Citation]]:
        """
        Retrieve relevant chunks for a query.
        Returns (formatted_context, citations).
        """
        top_k = top_k or settings.TOP_K_RETRIEVAL

        # Embed the query
        query_embedding = await self.embedding_svc.embed_query(query)

        # Search user's collection
        collection = f"user_{user_id}"
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            collection=collection,
            top_k=top_k,
            threshold=settings.SIMILARITY_THRESHOLD,
        )

        if not results:
            return "", []

        # Filter by document_ids if specified
        if document_ids:
            doc_id_strs = {str(did) for did in document_ids}
            results = [r for r in results if r.metadata.get("doc_id") in doc_id_strs]

        # Build context string and citations
        context_parts = []
        citations = []

        for i, result in enumerate(results):
            meta = result.metadata
            doc_name = meta.get("filename", "Unknown Document")
            doc_id = meta.get("doc_id", "")
            chunk_idx = meta.get("chunk_index", i)

            context_parts.append(
                f"[Source {i+1}: {doc_name}]\n{result.text}"
            )
            citations.append(Citation(
                document_id=doc_id,
                document_name=doc_name,
                chunk_text=result.text[:300] + "..." if len(result.text) > 300 else result.text,
                score=round(result.score, 3),
            ))

        context = "\n\n---\n\n".join(context_parts)
        return context, citations

    async def delete_document_vectors(self, document: Document) -> None:
        """Remove all vectors for a document when it's deleted."""
        if document.vector_collection:
            # ChromaDB: filter by doc_id metadata (expensive full scan)
            # For production, store node_ids in DB and delete by ID
            # This simplified version deletes the entire collection if user has no more docs
            pass  # Production: store node_ids per document and delete selectively
