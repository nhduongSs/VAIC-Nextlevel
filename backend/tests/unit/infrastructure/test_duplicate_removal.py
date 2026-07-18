"""Unit tests for DuplicateRemovalProcessor."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.dto.knowledge_dto import KnowledgeContext
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.knowledge.processors.duplicate_removal import DuplicateRemovalProcessor


def _chunk(chunk_id: object = None, score: float = 0.5) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id or uuid4(),  # type: ignore[arg-type]
        document_id=uuid4(),
        content="content",
        score=score,
        retrieval_method="hybrid",
    )


def _ctx(chunks: list[SearchResult]) -> KnowledgeContext:
    return KnowledgeContext(
        query="test",
        retrieved_chunks=chunks,
        ranked_chunks=list(chunks),
        document_map={},
    )


@pytest.mark.asyncio
async def test_no_duplicates_unchanged() -> None:
    chunks = [_chunk(), _chunk(), _chunk()]
    ctx = _ctx(chunks)
    await DuplicateRemovalProcessor().process(ctx)
    assert len(ctx.ranked_chunks) == 3
    assert ctx.statistics["duplicates_removed"] == 0


@pytest.mark.asyncio
async def test_duplicate_chunk_id_removed() -> None:
    cid = uuid4()
    c1 = _chunk(cid, score=0.9)
    c2 = _chunk(cid, score=0.7)
    c3 = _chunk(score=0.5)
    ctx = _ctx([c1, c2, c3])

    await DuplicateRemovalProcessor().process(ctx)

    assert len(ctx.ranked_chunks) == 2
    assert ctx.statistics["duplicates_removed"] == 1
    # First occurrence (highest score if sorted) is kept
    assert ctx.ranked_chunks[0].chunk_id == cid
    assert ctx.ranked_chunks[0].score == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_all_duplicates_collapsed_to_one() -> None:
    cid = uuid4()
    chunks = [_chunk(cid, score=float(i)) for i in range(5)]
    ctx = _ctx(chunks)
    await DuplicateRemovalProcessor().process(ctx)
    assert len(ctx.ranked_chunks) == 1
    assert ctx.statistics["duplicates_removed"] == 4


@pytest.mark.asyncio
async def test_empty_input() -> None:
    ctx = _ctx([])
    await DuplicateRemovalProcessor().process(ctx)
    assert ctx.ranked_chunks == []
    assert ctx.statistics["duplicates_removed"] == 0
