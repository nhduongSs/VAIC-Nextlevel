from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import ColumnElement, Float, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.search_dto import SearchFilters
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.ai.embedding.embedding_provider import EmbeddingProvider
from app.infrastructure.database.models.chunk_model import ChunkModel
from app.infrastructure.database.models.document_model import DocumentModel
from app.infrastructure.retrieval.metadata_filter import MetadataFilter
from app.utils.constants import HNSW_EF_SEARCH

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class VectorRetriever:
    """ANN similarity search via pgvector HNSW index (cosine distance)."""

    def __init__(
        self,
        session: AsyncSession,
        provider: EmbeddingProvider,
        metadata_filter: MetadataFilter,
        top_k: int = 20,
        score_threshold: float = 0.0,
    ) -> None:
        self._session = session
        self._provider = provider
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

        # Embed the query
        vectors = await self._provider.embed([query])
        query_vec = vectors[0]

        # Set HNSW ef_search for this transaction (per architecture A11)
        await self._session.execute(text(f"SET LOCAL hnsw.ef_search = {HNSW_EF_SEARCH}"))

        conditions: list[ColumnElement[Any]] = self._filter.build(filters)
        conditions.append(ChunkModel.embedding.is_not(None))

        # cosine similarity = 1 - cosine_distance; higher = better match
        # return_type=Float() prevents pgvector's bind_processor from being applied
        # to the literal `1` on the left side of the subtraction.
        vec_literal = "[" + ",".join(str(v) for v in query_vec) + "]"
        cosine_dist = ChunkModel.embedding.op("<=>", return_type=Float())(
            text(f"'{vec_literal}'::vector")
        )
        vector_score = (1 - cosine_dist).label("vector_score")

        stmt = (
            select(ChunkModel, vector_score)
            .join(DocumentModel, ChunkModel.document_id == DocumentModel.id)
            .where(*conditions)
            .order_by(vector_score.desc())
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
                    retrieval_method="vector",
                    vector_score=score,
                    chunk_index=chunk.chunk_index,
                    chunk_type=chunk.chunk_type,
                    section_title=chunk.section_title,
                    section_number=chunk.section_number,
                    page_number=chunk.page_number,
                    metadata=dict(chunk.metadata_extra) if chunk.metadata_extra else {},
                )
            )

        log.debug("vector_retrieve", query=query[:80], hits=len(results), top_k=k)
        return results
