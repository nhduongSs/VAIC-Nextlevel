from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import ColumnElement, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.search_dto import SearchFilters
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.database.models.chunk_model import ChunkModel
from app.infrastructure.database.models.document_model import DocumentModel
from app.infrastructure.retrieval.metadata_filter import MetadataFilter

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_TS_CONFIG = "simple"  # language-agnostic; works for Vietnamese without custom dict


class BM25Retriever:
    """Full-text search via PostgreSQL tsvector + ts_rank_cd."""

    def __init__(
        self,
        session: AsyncSession,
        metadata_filter: MetadataFilter,
        top_k: int = 20,
        score_threshold: float = 0.0,
    ) -> None:
        self._session = session
        self._filter = metadata_filter
        self._top_k = top_k
        self._score_threshold = score_threshold

    async def retrieve(
        self,
        query: str,
        filters: SearchFilters | None = None,
        top_k: int | None = None,
    ) -> list[SearchResult]:
        k = top_k or self._top_k
        tsquery = func.plainto_tsquery(text(f"'{_TS_CONFIG}'"), query)
        bm25_score = func.ts_rank_cd(ChunkModel.search_vector, tsquery).label("bm25_score")

        conditions: list[ColumnElement[Any]] = self._filter.build(filters)
        conditions.append(ChunkModel.search_vector.op("@@")(tsquery))

        stmt = (
            select(ChunkModel, bm25_score)
            .join(DocumentModel, ChunkModel.document_id == DocumentModel.id)
            .where(*conditions)
            .order_by(bm25_score.desc())
            .limit(k)
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        results: list[SearchResult] = []
        for row in rows:
            chunk: ChunkModel = row[0]
            score: float = float(row[1])
            if score < self._score_threshold:
                continue
            results.append(
                SearchResult(
                    chunk_id=UUID(str(chunk.id)),
                    document_id=UUID(str(chunk.document_id)),
                    content=chunk.content,
                    score=score,
                    retrieval_method="bm25",
                    bm25_score=score,
                    chunk_index=chunk.chunk_index,
                    chunk_type=chunk.chunk_type,
                    section_title=chunk.section_title,
                    section_number=chunk.section_number,
                    page_number=chunk.page_number,
                    metadata=dict(chunk.metadata_extra) if chunk.metadata_extra else {},
                )
            )

        log.debug("bm25_retrieve", query=query[:80], hits=len(results), top_k=k)
        return results
