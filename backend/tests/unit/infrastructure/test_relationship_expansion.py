"""Unit tests for RelationshipExpansionProcessor."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.dto.knowledge_dto import KnowledgeContext
from app.domain.entities.relation import DocumentRelation
from app.domain.value_objects.relation_type import RelationType
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.knowledge.processors.relationship_expansion import (
    RelationshipExpansionProcessor,
)


def _mock_session(relations: list[DocumentRelation] | None = None) -> AsyncMock:
    """Return a mock AsyncSession whose execute() returns the given relations."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    return session


def _rel(src_id: object, tgt_id: object) -> DocumentRelation:
    return DocumentRelation(
        id=uuid4(),
        source_doc_id=src_id,  # type: ignore[arg-type]
        target_doc_id=tgt_id,  # type: ignore[arg-type]
        relation_type=RelationType.REFERENCES,
        created_at=datetime.now(UTC),
    )


def _ctx_with_doc(
    doc_id: object, existing_rels: list[DocumentRelation] | None = None
) -> KnowledgeContext:
    chunk = SearchResult(
        chunk_id=uuid4(),
        document_id=doc_id,  # type: ignore[arg-type]
        content="content",
        score=0.8,
        retrieval_method="hybrid",
    )
    return KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk],
        ranked_chunks=[chunk],
        document_map={doc_id: MagicMock()},  # type: ignore[dict-item]
        relationships=list(existing_rels or []),
    )


@pytest.mark.asyncio
async def test_empty_doc_map_no_queries() -> None:
    session = _mock_session()
    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[],
        ranked_chunks=[],
        document_map={},
    )
    processor = RelationshipExpansionProcessor(session=session, max_depth=2)
    await processor.process(ctx)
    session.execute.assert_not_called()
    assert ctx.statistics["expansion_count"] == 0


@pytest.mark.asyncio
async def test_no_new_relations_expansion_count_zero() -> None:
    doc_id = uuid4()
    session = _mock_session()
    ctx = _ctx_with_doc(doc_id)
    processor = RelationshipExpansionProcessor(session=session, max_depth=2)
    await processor.process(ctx)
    assert ctx.statistics["expansion_count"] == 0


@pytest.mark.asyncio
async def test_existing_relations_not_double_counted() -> None:
    doc_a = uuid4()
    doc_b = uuid4()
    existing_rel = _rel(doc_a, doc_b)
    ctx = _ctx_with_doc(doc_a, existing_rels=[existing_rel])

    # Session returns the same relation (same id) — should not be added again
    mock_rel_model = MagicMock()
    mock_rel_model.id = existing_rel.id
    mock_rel_model.source_doc_id = doc_a
    mock_rel_model.target_doc_id = doc_b
    mock_rel_model.relation_type = RelationType.REFERENCES.value
    mock_rel_model.confidence = 1.0
    mock_rel_model.description = None
    mock_rel_model.metadata_extra = {}
    mock_rel_model.created_at = datetime.now(UTC)

    session = AsyncMock()
    # First execute = _fetch_documents for the initial frontier (doc_b); return []
    # Second execute = _fetch_relations for the BFS depth-0 frontier; return same relation
    doc_result = MagicMock()
    doc_result.scalars.return_value.all.return_value = []
    rel_result = MagicMock()
    rel_result.scalars.return_value.all.return_value = [mock_rel_model]
    session.execute.side_effect = [doc_result, rel_result]

    processor = RelationshipExpansionProcessor(session=session, max_depth=1)
    await processor.process(ctx)

    # expansion_count should be 0 because the relation was already known
    assert ctx.statistics["expansion_count"] == 0


@pytest.mark.asyncio
async def test_max_depth_zero_no_queries() -> None:
    doc_id = uuid4()
    session = _mock_session()
    ctx = _ctx_with_doc(doc_id)
    processor = RelationshipExpansionProcessor(session=session, max_depth=0)
    await processor.process(ctx)
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_max_relations_respected() -> None:
    doc_id = uuid4()

    # Pre-load 5 existing relations (already at max)
    existing_rels = [_rel(doc_id, uuid4()) for _ in range(5)]
    ctx = _ctx_with_doc(doc_id, existing_rels=existing_rels)

    session = _mock_session()
    processor = RelationshipExpansionProcessor(session=session, max_depth=2, max_relations=5)
    await processor.process(ctx)

    # Already at max — expansion loop should not add more
    assert len(ctx.relationships) == 5
    assert ctx.statistics["expansion_count"] == 0
