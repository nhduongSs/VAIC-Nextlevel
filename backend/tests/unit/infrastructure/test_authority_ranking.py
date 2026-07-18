"""Unit tests for AuthorityRankingProcessor."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.dto.knowledge_dto import KnowledgeContext
from app.domain.entities.document import Document
from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.knowledge.processors.authority_ranking import AuthorityRankingProcessor


def _doc(authority: AuthorityLevel) -> Document:
    did = uuid4()
    now = datetime.now(UTC)
    return Document(
        id=did,
        title="Doc",
        filename="doc.pdf",
        original_filename="doc.pdf",
        content_type="application/pdf",
        file_size=100,
        file_path="uploads/doc.pdf",
        content_hash="abc",
        status=DocumentStatus.READY,
        version=1,
        doc_type=DocumentType.CIRCULAR,
        authority_level=authority,
        created_at=now,
        updated_at=now,
    )


def _chunk(document_id: object, score: float = 0.5) -> SearchResult:
    return SearchResult(
        chunk_id=uuid4(),
        document_id=document_id,  # type: ignore[arg-type]
        content="content",
        score=score,
        retrieval_method="hybrid",
    )


def _ctx(chunks: list[SearchResult], docs: list[Document]) -> KnowledgeContext:
    return KnowledgeContext(
        query="test",
        retrieved_chunks=chunks,
        ranked_chunks=list(chunks),
        document_map={d.id: d for d in docs},
    )


@pytest.mark.asyncio
async def test_high_authority_increases_score() -> None:
    doc = _doc(AuthorityLevel.NATIONAL_LAW)
    chunk = _chunk(doc.id, score=0.5)
    ctx = _ctx([chunk], [doc])

    processor = AuthorityRankingProcessor(authority_weight=0.2)
    await processor.process(ctx)

    # NATIONAL_LAW authority_score = 1.0
    # new_score = 0.8 * 0.5 + 0.2 * 1.0 = 0.6
    assert ctx.ranked_chunks[0].score == pytest.approx(0.6, abs=1e-6)


@pytest.mark.asyncio
async def test_low_authority_lowers_score() -> None:
    doc = _doc(AuthorityLevel.FAQ)
    chunk = _chunk(doc.id, score=0.5)
    ctx = _ctx([chunk], [doc])

    processor = AuthorityRankingProcessor(authority_weight=0.2)
    await processor.process(ctx)

    # FAQ authority_score = 0.1
    # new_score = 0.8 * 0.5 + 0.2 * 0.1 = 0.42
    assert ctx.ranked_chunks[0].score == pytest.approx(0.42, abs=1e-6)


@pytest.mark.asyncio
async def test_missing_doc_in_map_gets_zero_authority() -> None:
    chunk = _chunk(uuid4(), score=0.6)
    ctx = _ctx([chunk], [])

    processor = AuthorityRankingProcessor(authority_weight=0.2)
    await processor.process(ctx)

    # No doc → authority_score = 0.0
    # new_score = 0.8 * 0.6 + 0.2 * 0.0 = 0.48
    assert ctx.ranked_chunks[0].score == pytest.approx(0.48, abs=1e-6)


@pytest.mark.asyncio
async def test_chunks_sorted_by_score_after_ranking() -> None:
    doc_high = _doc(AuthorityLevel.NATIONAL_LAW)
    doc_low = _doc(AuthorityLevel.FAQ)

    chunk_low_retrieval = _chunk(doc_high.id, score=0.3)
    chunk_high_retrieval = _chunk(doc_low.id, score=0.8)

    ctx = _ctx([chunk_high_retrieval, chunk_low_retrieval], [doc_high, doc_low])
    await AuthorityRankingProcessor(authority_weight=0.4).process(ctx)

    # After authority boosting, national law chunk may overtake FAQ chunk
    scores = [r.score for r in ctx.ranked_chunks]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_authority_level_added_to_metadata() -> None:
    doc = _doc(AuthorityLevel.NHNN_CIRCULAR)
    chunk = _chunk(doc.id)
    ctx = _ctx([chunk], [doc])

    await AuthorityRankingProcessor().process(ctx)

    assert ctx.ranked_chunks[0].metadata["authority_level"] == "NHNN_CIRCULAR"


@pytest.mark.asyncio
async def test_custom_authority_scores() -> None:
    doc = _doc(AuthorityLevel.NHNN_CIRCULAR)
    chunk = _chunk(doc.id, score=0.5)
    ctx = _ctx([chunk], [doc])

    custom = {"NHNN_CIRCULAR": 0.5}
    await AuthorityRankingProcessor(authority_scores=custom, authority_weight=0.2).process(ctx)

    assert ctx.ranked_chunks[0].score == pytest.approx(0.8 * 0.5 + 0.2 * 0.5, abs=1e-6)


@pytest.mark.asyncio
async def test_statistics_updated() -> None:
    doc = _doc(AuthorityLevel.NHNN_DECISION)
    ctx = _ctx([_chunk(doc.id)], [doc])
    await AuthorityRankingProcessor().process(ctx)
    assert ctx.statistics["authority_ranking_applied"] is True
