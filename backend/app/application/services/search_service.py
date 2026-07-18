from __future__ import annotations

import time

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.search_dto import SearchRequest
from app.application.retrieval import Retriever, RetrieverFactory
from app.config import settings
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.ai.embedding.embedding_provider import EmbeddingProvider
from app.infrastructure.retrieval.bm25_retriever import BM25Retriever
from app.infrastructure.retrieval.hybrid_retriever import HybridRetriever
from app.infrastructure.retrieval.metadata_filter import MetadataFilter
from app.infrastructure.retrieval.vector_retriever import VectorRetriever
from app.presentation.exceptions import AppException

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_MAX_QUERY_LENGTH = 1000


class SearchService:
    """Orchestrates the retrieval pipeline: validate → filter → hybrid search."""

    def __init__(
        self,
        session: AsyncSession,
        provider: EmbeddingProvider,
        retriever_factory: RetrieverFactory | None = None,
    ) -> None:
        self._provider = provider
        self._retriever_factory = retriever_factory or _HybridRetrieverFactory(session, provider)

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        self._validate(request)

        alpha = (
            request.vector_weight
            if request.vector_weight is not None
            else settings.SEARCH_HYBRID_ALPHA
        )
        beta = (
            request.bm25_weight if request.bm25_weight is not None else settings.SEARCH_HYBRID_BETA
        )
        top_k = min(request.top_k, settings.SEARCH_MAX_TOP_K)

        retriever = self._retriever_factory.create(alpha=alpha, beta=beta)

        t0 = time.perf_counter()
        results = await retriever.retrieve(
            query=request.query.strip(),
            filters=request.filters,
            top_k=top_k,
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        log.info(
            "search_completed",
            query=request.query[:80],
            top_k=top_k,
            results=len(results),
            latency_ms=round(latency_ms, 1),
            top_score=results[0].score if results else 0.0,
            alpha=alpha,
            beta=beta,
        )
        return results

    async def health(self) -> bool:
        return await self._provider.health_check()

    def _validate(self, request: SearchRequest) -> None:
        query = request.query.strip() if request.query else ""
        if not query:
            raise AppException(
                status_code=400, error="INVALID_QUERY", message="Query cannot be empty"
            )
        if len(query) > _MAX_QUERY_LENGTH:
            raise AppException(
                status_code=400,
                error="INVALID_QUERY",
                message=f"Query exceeds maximum length of {_MAX_QUERY_LENGTH} characters",
            )
        if request.top_k < 1:
            raise AppException(
                status_code=400, error="INVALID_QUERY", message="top_k must be at least 1"
            )
        if request.top_k > settings.SEARCH_MAX_TOP_K:
            raise AppException(
                status_code=400,
                error="INVALID_QUERY",
                message=f"top_k cannot exceed {settings.SEARCH_MAX_TOP_K}",
            )
        if request.vector_weight is not None and not (0.0 <= request.vector_weight <= 1.0):
            raise AppException(
                status_code=400,
                error="INVALID_QUERY",
                message="vector_weight must be between 0 and 1",
            )
        if request.bm25_weight is not None and not (0.0 <= request.bm25_weight <= 1.0):
            raise AppException(
                status_code=400,
                error="INVALID_QUERY",
                message="bm25_weight must be between 0 and 1",
            )
        if request.vector_weight is not None and request.bm25_weight is not None:
            total = request.vector_weight + request.bm25_weight
            if total <= 0.0 or total > 1.0:
                raise AppException(
                    status_code=400,
                    error="INVALID_QUERY",
                    message="vector_weight + bm25_weight must be greater than 0 and at most 1",
                )


class _HybridRetrieverFactory:
    def __init__(self, session: AsyncSession, provider: EmbeddingProvider) -> None:
        self._session = session
        self._provider = provider
        self._meta_filter = MetadataFilter()

    def create(self, *, alpha: float, beta: float) -> Retriever:
        bm25 = BM25Retriever(
            session=self._session,
            metadata_filter=self._meta_filter,
            top_k=settings.SEARCH_BM25_TOP_K,
            score_threshold=settings.SEARCH_BM25_THRESHOLD,
        )
        vector = VectorRetriever(
            session=self._session,
            provider=self._provider,
            metadata_filter=self._meta_filter,
            top_k=settings.SEARCH_VECTOR_TOP_K,
            score_threshold=settings.SEARCH_VECTOR_THRESHOLD,
        )
        return HybridRetriever(bm25=bm25, vector=vector, alpha=alpha, beta=beta)
