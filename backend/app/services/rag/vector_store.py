"""
Vector store abstraction — ChromaDB for dev, Pinecone for production.
Swap providers via VECTOR_DB_PROVIDER env var without changing RAG code.
"""
from typing import List, Optional, Protocol
from dataclasses import dataclass

from llama_index.core.schema import TextNode

from app.core.config import settings


@dataclass
class SearchResult:
    node_id: str
    text: str
    score: float
    metadata: dict


class VectorStore(Protocol):
    async def upsert(self, nodes: List[TextNode], collection: str) -> None: ...
    async def search(self, query_embedding: List[float], collection: str, top_k: int, threshold: float) -> List[SearchResult]: ...
    async def delete_collection(self, collection: str) -> None: ...


class ChromaVectorStore:
    def __init__(self):
        import chromadb
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )

    def _get_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    async def upsert(self, nodes: List[TextNode], collection: str) -> None:
        col = self._get_collection(collection)
        col.upsert(
            ids=[node.node_id for node in nodes],
            documents=[node.text for node in nodes],
            metadatas=[node.metadata for node in nodes],
            embeddings=[node.embedding for node in nodes if node.embedding],
        )

    async def search(
        self,
        query_embedding: List[float],
        collection: str,
        top_k: int = 6,
        threshold: float = 0.7,
    ) -> List[SearchResult]:
        col = self._get_collection(collection)
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            score = 1 - dist  # Chroma returns cosine distance → convert to similarity
            if score >= threshold:
                search_results.append(SearchResult(
                    node_id=results["ids"][0][i],
                    text=doc,
                    score=score,
                    metadata=meta,
                ))

        return sorted(search_results, key=lambda x: x.score, reverse=True)

    async def delete_collection(self, collection: str) -> None:
        try:
            self.client.delete_collection(collection)
        except Exception:
            pass


class PineconeVectorStore:
    def __init__(self):
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index = pc.Index(settings.PINECONE_INDEX_NAME)

    async def upsert(self, nodes: List[TextNode], collection: str) -> None:
        vectors = []
        for node in nodes:
            if node.embedding:
                vectors.append({
                    "id": node.node_id,
                    "values": node.embedding,
                    "metadata": {**node.metadata, "text": node.text[:1000]},
                })
        if vectors:
            # Pinecone uses namespaces to partition — collection = namespace
            self.index.upsert(vectors=vectors, namespace=collection)

    async def search(
        self,
        query_embedding: List[float],
        collection: str,
        top_k: int = 6,
        threshold: float = 0.7,
    ) -> List[SearchResult]:
        response = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=collection,
            include_metadata=True,
        )
        results = []
        for match in response.matches:
            if match.score >= threshold:
                results.append(SearchResult(
                    node_id=match.id,
                    text=match.metadata.get("text", ""),
                    score=match.score,
                    metadata=match.metadata,
                ))
        return results

    async def delete_collection(self, collection: str) -> None:
        self.index.delete(delete_all=True, namespace=collection)


def get_vector_store() -> VectorStore:
    if settings.VECTOR_DB_PROVIDER == "pinecone":
        return PineconeVectorStore()
    return ChromaVectorStore()
