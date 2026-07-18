"""Unit tests for ContextBuilderProcessor."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.dto.knowledge_dto import (
    Citation,
    ConflictInfo,
    KnowledgeContext,
    TimelineEntry,
)
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.knowledge.processors.context_builder import ContextBuilderProcessor


def _chunk(score: float = 0.8) -> SearchResult:
    return SearchResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        content="content",
        score=score,
        retrieval_method="hybrid",
    )


def _ctx(chunks: list[SearchResult]) -> KnowledgeContext:
    return KnowledgeContext(
        query="test query",
        retrieved_chunks=chunks,
        ranked_chunks=list(chunks),
        document_map={},
    )


@pytest.mark.asyncio
async def test_context_package_assembled() -> None:
    chunks = [_chunk() for _ in range(3)]
    ctx = _ctx(chunks)
    await ContextBuilderProcessor().process(ctx)

    assert ctx.context_package is not None
    assert ctx.context_package.query == "test query"
    assert len(ctx.context_package.ranked_chunks) == 3


@pytest.mark.asyncio
async def test_max_chunks_enforced() -> None:
    chunks = [_chunk() for _ in range(20)]
    ctx = _ctx(chunks)
    await ContextBuilderProcessor(max_chunks=5).process(ctx)

    assert len(ctx.context_package.ranked_chunks) == 5  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_max_citations_enforced() -> None:
    chunk = _chunk()
    ctx = _ctx([chunk])
    ctx.citations = [
        Citation(
            chunk_id=uuid4(),
            document_id=uuid4(),
            document_title="T",
            doc_number=None,
            section_title=None,
            section_number=None,
            page_number=None,
            chunk_index=0,
            authority_level="NHNN_CIRCULAR",
            version=1,
            effective_date=None,
            content_preview="p",
        )
        for _ in range(15)
    ]
    await ContextBuilderProcessor(max_citations=5).process(ctx)
    assert len(ctx.context_package.citations) == 5  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_statistics_updated_in_package() -> None:
    chunks = [_chunk() for _ in range(4)]
    ctx = _ctx(chunks)
    await ContextBuilderProcessor(max_chunks=10).process(ctx)

    stats = ctx.context_package.statistics  # type: ignore[union-attr]
    assert stats["ranked_chunk_count"] == 4
    assert stats["citation_count"] == 0
    assert stats["conflict_count"] == 0
    assert stats["timeline_entry_count"] == 0


@pytest.mark.asyncio
async def test_conflicts_and_timeline_passed_through() -> None:
    did_a = uuid4()
    did_b = uuid4()
    chunk = _chunk()
    ctx = _ctx([chunk])
    ctx.conflicts = [
        ConflictInfo(
            source_doc_id=did_a,
            target_doc_id=did_b,
            source_title="A",
            target_title="B",
            description=None,
            confidence=0.8,
        )
    ]
    ctx.timeline = [
        TimelineEntry(
            document_id=did_a,
            document_title="A",
            doc_number="01",
            version=1,
            effective_date=None,
            issued_date=None,
            relation_type=None,
            is_current=False,
        )
    ]
    await ContextBuilderProcessor().process(ctx)
    assert len(ctx.context_package.conflicts) == 1  # type: ignore[union-attr]
    assert len(ctx.context_package.timeline) == 1  # type: ignore[union-attr]
