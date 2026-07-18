"""Unit tests for VersionResolutionProcessor."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.dto.knowledge_dto import KnowledgeContext
from app.domain.entities.relation import DocumentRelation
from app.domain.value_objects.relation_type import RelationType
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.knowledge.processors.version_resolution import VersionResolutionProcessor


def _chunk(document_id: object, score: float = 0.8) -> SearchResult:
    return SearchResult(
        chunk_id=uuid4(),
        document_id=document_id,  # type: ignore[arg-type]
        content="content",
        score=score,
        retrieval_method="hybrid",
    )


def _replaces(source_id: object, target_id: object) -> DocumentRelation:
    return DocumentRelation(
        id=uuid4(),
        source_doc_id=source_id,  # type: ignore[arg-type]
        target_doc_id=target_id,  # type: ignore[arg-type]
        relation_type=RelationType.REPLACES,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_superseded_chunk_score_penalized() -> None:
    old_doc_id = uuid4()
    new_doc_id = uuid4()
    old_chunk = _chunk(old_doc_id, score=0.8)
    new_chunk = _chunk(new_doc_id, score=0.7)
    rel = _replaces(new_doc_id, old_doc_id)  # new_doc replaces old_doc

    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[old_chunk, new_chunk],
        ranked_chunks=[old_chunk, new_chunk],
        document_map={},
        relationships=[rel],
    )

    await VersionResolutionProcessor(superseded_penalty=0.5).process(ctx)

    assert old_chunk.score == pytest.approx(0.4, abs=1e-6)
    assert new_chunk.score == pytest.approx(0.7, abs=1e-6)
    assert old_chunk.metadata["superseded"] is True
    assert new_chunk.metadata["superseded"] is False


@pytest.mark.asyncio
async def test_no_replaces_relations_no_penalty() -> None:
    doc_id = uuid4()
    chunk = _chunk(doc_id, score=0.9)
    rel = DocumentRelation(
        id=uuid4(),
        source_doc_id=uuid4(),
        target_doc_id=uuid4(),
        relation_type=RelationType.REFERENCES,
        created_at=datetime.now(UTC),
    )

    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk],
        ranked_chunks=[chunk],
        document_map={},
        relationships=[rel],
    )

    await VersionResolutionProcessor().process(ctx)

    assert chunk.score == pytest.approx(0.9, abs=1e-6)
    assert chunk.metadata["superseded"] is False


@pytest.mark.asyncio
async def test_superseded_chunks_re_sorted() -> None:
    old_id = uuid4()
    new_id = uuid4()
    old_chunk = _chunk(old_id, score=0.9)
    new_chunk = _chunk(new_id, score=0.5)
    rel = _replaces(new_id, old_id)

    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[old_chunk, new_chunk],
        ranked_chunks=[old_chunk, new_chunk],
        document_map={},
        relationships=[rel],
    )

    await VersionResolutionProcessor(superseded_penalty=0.5).process(ctx)

    # old_chunk score = 0.9 * 0.5 = 0.45; new_chunk score = 0.5
    # After sort: new_chunk first
    assert ctx.ranked_chunks[0].document_id == new_id


@pytest.mark.asyncio
async def test_empty_relationships_no_change() -> None:
    chunk = _chunk(uuid4(), score=0.7)
    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk],
        ranked_chunks=[chunk],
        document_map={},
        relationships=[],
    )
    original_score = chunk.score
    await VersionResolutionProcessor().process(ctx)
    assert chunk.score == pytest.approx(original_score)


@pytest.mark.asyncio
async def test_statistics_updated() -> None:
    old_id = uuid4()
    chunk = _chunk(old_id)
    rel = _replaces(uuid4(), old_id)
    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk],
        ranked_chunks=[chunk],
        document_map={},
        relationships=[rel],
    )
    await VersionResolutionProcessor().process(ctx)
    assert ctx.statistics["superseded_count"] == 1
