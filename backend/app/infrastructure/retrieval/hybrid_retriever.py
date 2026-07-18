from __future__ import annotations

import asyncio
from uuid import UUID

import structlog

from app.application.dto.search_dto import SearchFilters
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.retrieval.bm25_retriever import BM25Retriever
from app.infrastructure.retrieval.score_normalizer import min_max_normalize
from app.infrastructure.retrieval.vector_retriever import VectorRetriever

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class HybridRetriever:
    """Combines BM25 and Vector retrieval with configurable score weighting.

    Hybrid score = alpha * vector_score_normalized + beta * bm25_score_normalized
    """

    def __init__(
        self,
        bm25: BM25Retriever,
        vector: VectorRetriever,
        alpha: float = 0.7,  # vector weight
        beta: float = 0.3,  # bm25 weight
    ) -> None:
        self._bm25 = bm25
        self._vector = vector
        self._alpha = alpha
        self._beta = beta

    async def retrieve(
        self,
        query: str,
        filters: SearchFilters | None = None,
        top_k: int = 10,
        candidate_k: int | None = None,
    ) -> list[SearchResult]:
        fetch_k = candidate_k or top_k * 3

        # Run BM25 and Vector retrieval concurrently
        bm25_results, vector_results = await asyncio.gather(
            self._bm25.retrieve(query, filters, fetch_k),
            self._vector.retrieve(query, filters, fetch_k),
        )

        # Normalize scores within each set independently
        bm25_norm = _normalize_results(bm25_results, "bm25_score")
        vector_norm = _normalize_results(vector_results, "vector_score")

        # Merge into chunk_id → SearchResult map; combine scores
        merged: dict[UUID, SearchResult] = {}

        for res in vector_norm:
            merged[res.chunk_id] = SearchResult(
                chunk_id=res.chunk_id,
                document_id=res.document_id,
                content=res.content,
                score=self._alpha * (res.vector_score or 0.0),
                retrieval_method="hybrid",
                vector_score=res.vector_score,
                bm25_score=None,
                chunk_index=res.chunk_index,
                chunk_type=res.chunk_type,
                section_title=res.section_title,
                section_number=res.section_number,
                page_number=res.page_number,
                metadata=res.metadata,
            )

        for res in bm25_norm:
            if res.chunk_id in merged:
                existing = merged[res.chunk_id]
                existing.score += self._beta * (res.bm25_score or 0.0)
                existing.bm25_score = res.bm25_score
            else:
                merged[res.chunk_id] = SearchResult(
                    chunk_id=res.chunk_id,
                    document_id=res.document_id,
                    content=res.content,
                    score=self._beta * (res.bm25_score or 0.0),
                    retrieval_method="hybrid",
                    vector_score=None,
                    bm25_score=res.bm25_score,
                    chunk_index=res.chunk_index,
                    chunk_type=res.chunk_type,
                    section_title=res.section_title,
                    section_number=res.section_number,
                    page_number=res.page_number,
                    metadata=res.metadata,
                )

        ranked = sorted(merged.values(), key=lambda r: r.score, reverse=True)[:top_k]

        log.debug(
            "hybrid_retrieve",
            query=query[:80],
            bm25_hits=len(bm25_results),
            vector_hits=len(vector_results),
            merged_total=len(merged),
            returned=len(ranked),
            top_score=ranked[0].score if ranked else 0.0,
        )
        return ranked


def _normalize_results(results: list[SearchResult], score_field: str) -> list[SearchResult]:
    """Normalize the specified score field via min-max and update `.score`."""
    if not results:
        return results
    raw = [getattr(r, score_field) or 0.0 for r in results]
    normed = min_max_normalize(raw)
    for result, norm_score in zip(results, normed, strict=True):
        setattr(result, score_field, norm_score)
        result.score = norm_score
    return results
