"""
Embedding service — wraps OpenAI and Sentence Transformers.
Provides a unified interface so the RAG pipeline doesn't care which model is used.
"""
from typing import List, Optional
import hashlib
import numpy as np

from app.core.config import settings


def _has_valid_openai_key() -> bool:
    return bool(settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"))


class EmbeddingService:
    _instance: Optional["EmbeddingService"] = None
    _st_model = None  # Sentence Transformer (lazy loaded)

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def embed_texts(self, texts: List[str], use_openai: bool = True) -> List[List[float]]:
        if use_openai and _has_valid_openai_key():
            return await self._embed_openai(texts)
        return self._embed_sentence_transformers(texts)

    async def embed_query(self, text: str, use_openai: bool = True) -> List[float]:
        embeddings = await self.embed_texts([text], use_openai=use_openai)
        return embeddings[0]

    async def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # OpenAI has a max batch size of 2048 inputs
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=batch,
            )
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings

    def _embed_sentence_transformers(self, texts: List[str]) -> List[List[float]]:
        try:
            if self._st_model is None:
                from sentence_transformers import SentenceTransformer
                self._st_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)

            embeddings = self._st_model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
            return embeddings.tolist()
        except Exception:
            return [self._embed_hash(text) for text in texts]

    def _embed_hash(self, text: str, dimensions: int = 384) -> List[float]:
        """Tiny local fallback so retrieval never blocks chat in dev mode."""
        vector = np.zeros(dimensions, dtype=np.float32)
        tokens = text.lower().split()
        for token in tokens or [text.lower()]:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[idx] += sign
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()
