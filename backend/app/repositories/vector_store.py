"""Merged retrieval classes: EmbeddingClient, MetadataFilter, ScoreNormalizer,
VectorRetriever, BM25Retriever, HybridRetriever.

Also provides get_hybrid_retriever() factory.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import ColumnElement, Float, cast, func, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SearchResult
from app.models.orm import ChunkModel, DocumentModel

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

HNSW_EF_SEARCH = 64
_MODEL_NAME = "BAAI/bge-m3"
_DIMENSIONS = 1024
_DEFAULT_TIMEOUT = 60.0
_TS_CONFIG = "simple"


# ── EmbeddingProvider (abstract) ──────────────────────────────────────────────


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...


# ── EmbeddingClient (BgeM3Client) ─────────────────────────────────────────────


class EmbeddingClient(EmbeddingProvider):
    """BGE-M3 embedding client via HTTP."""

    def __init__(self, base_url: str, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return _MODEL_NAME

    @property
    def dimensions(self) -> int:
        return _DIMENSIONS

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/embed",
                json={"texts": texts},
            )
            response.raise_for_status()
            data = response.json()
        embeddings: list[list[float]] = data["embeddings"]
        if len(embeddings) != len(texts):
            raise ValueError(
                f"Embedding count mismatch: expected {len(texts)}, got {len(embeddings)}"
            )
        for i, vec in enumerate(embeddings):
            if len(vec) != _DIMENSIONS:
                raise ValueError(
                    f"Embedding[{i}] has {len(vec)} dimensions, expected {_DIMENSIONS}"
                )
        return embeddings

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/health")
                return resp.status_code == 200
        except Exception:
            log.warning("bge_m3_health_check_failed", base_url=self._base_url)
            return False


# ── SearchFilters dataclass (inline to avoid circular import) ─────────────────


@dataclass
class SearchFilters:
    doc_type: str | None = None
    authority_level: str | None = None
    department: str | None = None
    language: str | None = None
    version: int | None = None
    effective_date_from: date | None = None
    effective_date_to: date | None = None
    tags: list[str] = field(default_factory=list)
    document_ids: list[UUID] = field(default_factory=list)
    bank: str | None = None
    category: str | None = None
    exclude_expired: bool = True
    doc_class: str | None = None
    doi_tuong: str | None = None


@dataclass
class SearchRequest:
    query: str
    top_k: int = 10
    filters: SearchFilters | None = None
    vector_weight: float | None = None
    bm25_weight: float | None = None


# ── MetadataFilter ────────────────────────────────────────────────────────────


class MetadataFilter:
    """Builds SQLAlchemy WHERE conditions from SearchFilters."""

    def build(self, filters: SearchFilters | None) -> list[ColumnElement[Any]]:
        conditions: list[ColumnElement[Any]] = [
            DocumentModel.deleted_at.is_(None),
        ]
        if filters is None:
            return conditions

        if filters.doc_type:
            conditions.append(DocumentModel.doc_type == filters.doc_type)

        if filters.authority_level:
            conditions.append(DocumentModel.authority_level == filters.authority_level)

        if filters.department:
            conditions.append(
                DocumentModel.metadata_extra["department"].astext == filters.department
            )

        if filters.language:
            conditions.append(
                DocumentModel.metadata_extra["language"].astext == filters.language
            )

        if filters.version:
            conditions.append(DocumentModel.version == filters.version)

        if filters.effective_date_from:
            conditions.append(
                DocumentModel.effective_date >= filters.effective_date_from
            )

        if filters.effective_date_to:
            conditions.append(DocumentModel.effective_date <= filters.effective_date_to)

        if filters.tags:
            for tag in filters.tags:
                conditions.append(DocumentModel.tags.op("@>")(cast([tag], JSONB)))

        if filters.document_ids:
            conditions.append(ChunkModel.document_id.in_(filters.document_ids))

        if filters.bank:
            conditions.append(
                DocumentModel.metadata_extra["bank"].astext == filters.bank
            )

        if filters.category:
            conditions.append(
                DocumentModel.metadata_extra["category"].astext == filters.category
            )

        if filters.exclude_expired:
            conditions.append(
                or_(
                    DocumentModel.metadata_extra["legal_status"].astext.is_(None),
                    DocumentModel.metadata_extra["legal_status"].astext != "het_hieu_luc",
                )
            )

        if filters.doc_class:
            conditions.append(
                DocumentModel.metadata_extra["doc_class"].astext == filters.doc_class
            )

        if filters.doi_tuong:
            conditions.append(
                DocumentModel.metadata_extra["doi_tuong_ap_dung"].op("@>")(
                    cast([filters.doi_tuong], JSONB)
                )
            )

        return conditions


# ── ScoreNormalizer ───────────────────────────────────────────────────────────


def min_max_normalize(scores: list[float]) -> list[float]:
    """Scale scores to [0, 1] using min-max normalization."""
    if not scores:
        return []
    min_s = min(scores)
    max_s = max(scores)
    if max_s == min_s:
        return [1.0] * len(scores)
    span = max_s - min_s
    return [(s - min_s) / span for s in scores]


# ── VectorRetriever ───────────────────────────────────────────────────────────


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

        vectors = await self._provider.embed([query])
        query_vec = vectors[0]

        await self._session.execute(
            text(f"SET LOCAL hnsw.ef_search = {HNSW_EF_SEARCH}")
        )

        conditions: list[ColumnElement[Any]] = self._filter.build(filters)
        conditions.append(ChunkModel.embedding.is_not(None))

        vec_literal = "[" + ",".join(str(v) for v in query_vec) + "]"
        cosine_dist = ChunkModel.embedding.op("<=>", return_type=Float())(
            text(f"'{vec_literal}'::vector")
        )
        vector_score = (1 - cosine_dist).label("vector_score")

        stmt = (
            select(ChunkModel, DocumentModel.metadata_extra, vector_score)
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
            doc_meta: dict[str, Any] = dict(row[1]) if row[1] else {}
            score: float = float(row[2])
            if score < self._score_threshold:
                continue
            chunk_meta = dict(chunk.metadata_extra) if chunk.metadata_extra else {}
            merged = {**doc_meta, **chunk_meta}
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
                    bank=merged.get("bank"),
                    category=merged.get("category"),
                    metadata=merged,
                )
            )

        log.debug("vector_retrieve", query=query[:80], hits=len(results), top_k=k)
        return results


# ── BM25Retriever ─────────────────────────────────────────────────────────────


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
        bm25_score = func.ts_rank_cd(ChunkModel.search_vector, tsquery).label(
            "bm25_score"
        )

        conditions: list[ColumnElement[Any]] = self._filter.build(filters)
        conditions.append(ChunkModel.search_vector.op("@@")(tsquery))

        stmt = (
            select(ChunkModel, DocumentModel.metadata_extra, bm25_score)
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
            doc_meta: dict[str, Any] = dict(row[1]) if row[1] else {}
            score: float = float(row[2])
            if score < self._score_threshold:
                continue
            chunk_meta = dict(chunk.metadata_extra) if chunk.metadata_extra else {}
            merged = {**doc_meta, **chunk_meta}
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
                    bank=merged.get("bank"),
                    category=merged.get("category"),
                    metadata=merged,
                )
            )

        log.debug("bm25_retrieve", query=query[:80], hits=len(results), top_k=k)
        return results


# ── HybridRetriever ───────────────────────────────────────────────────────────


class HybridRetriever:
    """Combines BM25 and Vector retrieval with configurable score weighting.

    Hybrid score = alpha * vector_score_normalized + beta * bm25_score_normalized
    """

    def __init__(
        self,
        bm25: BM25Retriever,
        vector: VectorRetriever,
        alpha: float = 0.7,
        beta: float = 0.3,
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

        bm25_results, vector_results = await asyncio.gather(
            self._bm25.retrieve(query, filters, fetch_k),
            self._vector.retrieve(query, filters, fetch_k),
        )

        bm25_norm = _normalize_results(bm25_results, "bm25_score")
        vector_norm = _normalize_results(vector_results, "vector_score")

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
                bank=res.bank,
                category=res.category,
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
                    bank=res.bank,
                    category=res.category,
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


def _normalize_results(
    results: list[SearchResult], score_field: str
) -> list[SearchResult]:
    """Normalize the specified score field via min-max and update `.score`."""
    if not results:
        return results
    raw = [getattr(r, score_field) or 0.0 for r in results]
    normed = min_max_normalize(raw)
    for result, norm_score in zip(results, normed, strict=True):
        setattr(result, score_field, norm_score)
        result.score = norm_score
    return results


# ── Factory ───────────────────────────────────────────────────────────────────


def get_hybrid_retriever(
    session: AsyncSession,
    embedding_client: EmbeddingClient,
    alpha: float = 0.7,
    beta: float = 0.3,
    bm25_top_k: int = 20,
    bm25_threshold: float = 0.0,
    vector_top_k: int = 20,
    vector_threshold: float = 0.0,
) -> HybridRetriever:
    """Factory function to create a HybridRetriever with all dependencies."""
    meta_filter = MetadataFilter()
    bm25 = BM25Retriever(
        session=session,
        metadata_filter=meta_filter,
        top_k=bm25_top_k,
        score_threshold=bm25_threshold,
    )
    vector = VectorRetriever(
        session=session,
        provider=embedding_client,
        metadata_filter=meta_filter,
        top_k=vector_top_k,
        score_threshold=vector_threshold,
    )
    return HybridRetriever(bm25=bm25, vector=vector, alpha=alpha, beta=beta)
