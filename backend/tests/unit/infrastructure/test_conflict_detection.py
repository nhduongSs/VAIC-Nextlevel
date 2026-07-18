"""Unit tests for ConflictDetectionProcessor."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.dto.knowledge_dto import KnowledgeContext
from app.domain.entities.relation import DocumentRelation
from app.domain.value_objects.relation_type import RelationType
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.knowledge.processors.conflict_detection import ConflictDetectionProcessor


def _chunk(document_id: object) -> SearchResult:
    return SearchResult(
        chunk_id=uuid4(),
        document_id=document_id,  # type: ignore[arg-type]
        content="content",
        score=0.8,
        retrieval_method="hybrid",
    )


def _conflict_rel(src: object, tgt: object, desc: str | None = None) -> DocumentRelation:
    return DocumentRelation(
        id=uuid4(),
        source_doc_id=src,  # type: ignore[arg-type]
        target_doc_id=tgt,  # type: ignore[arg-type]
        relation_type=RelationType.CONFLICTS_WITH,
        confidence=0.9,
        description=desc,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_conflict_detected_for_retrieved_docs() -> None:
    doc_a = uuid4()
    doc_b = uuid4()
    chunk_a = _chunk(doc_a)
    chunk_b = _chunk(doc_b)
    rel = _conflict_rel(doc_a, doc_b, "Contradictory rates")

    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk_a, chunk_b],
        ranked_chunks=[chunk_a, chunk_b],
        document_map={},
        relationships=[rel],
    )

    await ConflictDetectionProcessor().process(ctx)

    assert len(ctx.conflicts) == 1
    assert ctx.conflicts[0].source_doc_id == doc_a
    assert ctx.conflicts[0].target_doc_id == doc_b
    assert ctx.conflicts[0].description == "Contradictory rates"
    assert ctx.metadata.get("has_conflicts") is True


@pytest.mark.asyncio
async def test_conflict_ignored_if_neither_doc_retrieved() -> None:
    doc_a = uuid4()
    doc_b = uuid4()
    retrieved_doc = uuid4()
    chunk = _chunk(retrieved_doc)
    rel = _conflict_rel(doc_a, doc_b)

    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk],
        ranked_chunks=[chunk],
        document_map={},
        relationships=[rel],
    )

    await ConflictDetectionProcessor().process(ctx)

    assert ctx.conflicts == []


@pytest.mark.asyncio
async def test_no_conflicts_no_metadata_flag() -> None:
    chunk = _chunk(uuid4())
    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk],
        ranked_chunks=[chunk],
        document_map={},
        relationships=[],
    )
    await ConflictDetectionProcessor().process(ctx)
    assert ctx.conflicts == []
    assert "has_conflicts" not in ctx.metadata


@pytest.mark.asyncio
async def test_non_conflict_relation_ignored() -> None:
    doc_a = uuid4()
    doc_b = uuid4()
    chunk = _chunk(doc_a)
    rel = DocumentRelation(
        id=uuid4(),
        source_doc_id=doc_a,
        target_doc_id=doc_b,
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
    await ConflictDetectionProcessor().process(ctx)
    assert ctx.conflicts == []


@pytest.mark.asyncio
async def test_conflict_count_in_statistics() -> None:
    doc_a = uuid4()
    doc_b = uuid4()
    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[_chunk(doc_a), _chunk(doc_b)],
        ranked_chunks=[_chunk(doc_a), _chunk(doc_b)],
        document_map={},
        relationships=[_conflict_rel(doc_a, doc_b)],
    )
    await ConflictDetectionProcessor().process(ctx)
    assert ctx.statistics["conflict_count"] == 1


@pytest.mark.asyncio
async def test_disabled_processor_skips_detection() -> None:
    doc_a = uuid4()
    doc_b = uuid4()
    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[_chunk(doc_a), _chunk(doc_b)],
        ranked_chunks=[_chunk(doc_a), _chunk(doc_b)],
        document_map={},
        relationships=[_conflict_rel(doc_a, doc_b)],
    )
    await ConflictDetectionProcessor(enabled=False).process(ctx)
    assert ctx.conflicts == []
    assert ctx.statistics["conflict_count"] == 0
