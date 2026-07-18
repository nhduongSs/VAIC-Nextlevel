"""RAGService — wraps SearchService from application/services/search_service.py.
Provides retrieve() and build_context_block().
"""

from __future__ import annotations

import time

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.enums import SearchResult
from app.repositories.vector_store import (
    BM25Retriever,
    EmbeddingClient,
    HybridRetriever,
    MetadataFilter,
    SearchFilters,
    SearchRequest,
    VectorRetriever,
)

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_MAX_QUERY_LENGTH = 1000


class RAGService:
    """Orchestrates the retrieval pipeline: validate → filter → hybrid search."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_client: EmbeddingClient,
    ) -> None:
        self._session = session
        self._embedding_client = embedding_client
        self._meta_filter = MetadataFilter()

    def _build_retriever(self, alpha: float, beta: float) -> HybridRetriever:
        bm25 = BM25Retriever(
            session=self._session,
            metadata_filter=self._meta_filter,
            top_k=settings.SEARCH_BM25_TOP_K,
            score_threshold=settings.SEARCH_BM25_THRESHOLD,
        )
        vector = VectorRetriever(
            session=self._session,
            provider=self._embedding_client,
            metadata_filter=self._meta_filter,
            top_k=settings.SEARCH_VECTOR_TOP_K,
            score_threshold=settings.SEARCH_VECTOR_THRESHOLD,
        )
        return HybridRetriever(bm25=bm25, vector=vector, alpha=alpha, beta=beta)

    async def retrieve(
        self,
        query: str,
        filters: SearchFilters | None = None,
        top_k: int | None = None,
        vector_weight: float | None = None,
        bm25_weight: float | None = None,
    ) -> list[SearchResult]:
        """Retrieve chunks using hybrid search."""
        self._validate_query(query)
        alpha = (
            vector_weight if vector_weight is not None else settings.SEARCH_HYBRID_ALPHA
        )
        beta = bm25_weight if bm25_weight is not None else settings.SEARCH_HYBRID_BETA
        k = min(top_k or settings.SEARCH_DEFAULT_TOP_K, settings.SEARCH_MAX_TOP_K)

        retriever = self._build_retriever(alpha=alpha, beta=beta)

        t0 = time.perf_counter()
        results = await retriever.retrieve(
            query=query.strip(),
            filters=filters,
            top_k=k,
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        log.info(
            "rag_retrieve_completed",
            query=query[:80],
            top_k=k,
            results=len(results),
            latency_ms=round(latency_ms, 1),
            alpha=alpha,
            beta=beta,
        )
        return results

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        """Search using a SearchRequest DTO (compatible with existing routes)."""
        return await self.retrieve(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
            vector_weight=request.vector_weight,
            bm25_weight=request.bm25_weight,
        )

    async def health(self) -> bool:
        return await self._embedding_client.health_check()

    @staticmethod
    def build_context_block(chunks: list[SearchResult] | object) -> str:
        """Build context block for LLM from ranked chunks.
        Accepts either list[SearchResult] or a ContextPackage (from KI pipeline).
        """
        # If passed a ContextPackage, use ranked_chunks
        if hasattr(chunks, "ranked_chunks"):
            chunk_list = chunks.ranked_chunks
        else:
            chunk_list = chunks

        parts = []
        for i, c in enumerate(chunk_list, 1):
            section = ""
            if getattr(c, "section_number", None):
                section += f" | Điều {c.section_number}"
            if getattr(c, "section_title", None):
                section += f": {c.section_title}"
            parts.append(f"[Nguồn {i}{section}]\n{c.content}")
        return "\n\n".join(parts)

    def _validate_query(self, query: str) -> None:
        q = query.strip() if query else ""
        if not q:
            raise AppException(
                status_code=400, error="INVALID_QUERY", message="Query cannot be empty"
            )
        if len(q) > _MAX_QUERY_LENGTH:
            raise AppException(
                status_code=400,
                error="INVALID_QUERY",
                message=f"Query exceeds maximum length of {_MAX_QUERY_LENGTH} characters",
            )
