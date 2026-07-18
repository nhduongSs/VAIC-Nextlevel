"""Unit tests for TimelineProcessor."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.application.dto.knowledge_dto import KnowledgeContext
from app.domain.entities.document import Document
from app.domain.entities.relation import DocumentRelation
from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType
from app.domain.value_objects.relation_type import RelationType
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.knowledge.processors.timeline_processor import TimelineProcessor


def _doc(doc_number: str, version: int = 1, eff: date | None = None) -> Document:
    now = datetime.now(UTC)
    did = uuid4()
    return Document(
        id=did,
        title=f"Thông tư {doc_number}",
        filename="f.docx",
        original_filename="f.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size=100,
        file_path="uploads/f.docx",
        content_hash=doc_number,
        status=DocumentStatus.READY,
        version=version,
        doc_type=DocumentType.CIRCULAR,
        authority_level=AuthorityLevel.NHNN_CIRCULAR,
        created_at=now,
        updated_at=now,
        doc_number=doc_number,
        effective_date=eff,
    )


def _replaces(src: Document, tgt: Document) -> DocumentRelation:
    return DocumentRelation(
        id=uuid4(),
        source_doc_id=src.id,
        target_doc_id=tgt.id,
        relation_type=RelationType.REPLACES,
        created_at=datetime.now(UTC),
    )


def _ctx(docs: list[Document], rels: list[DocumentRelation]) -> KnowledgeContext:
    chunk = SearchResult(
        chunk_id=uuid4(),
        document_id=docs[0].id,
        content="content",
        score=0.8,
        retrieval_method="hybrid",
    )
    return KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk],
        ranked_chunks=[chunk],
        document_map={d.id: d for d in docs},
        relationships=rels,
    )


@pytest.mark.asyncio
async def test_linear_chain_built_oldest_to_newest() -> None:
    doc_2014 = _doc("01/2014/TT-NHNN", eff=date(2014, 1, 1))
    doc_2022 = _doc("18/2022/TT-NHNN", eff=date(2022, 6, 1))
    doc_2024 = _doc("48/2024/TT-NHNN", eff=date(2024, 7, 1))

    # 2022 replaces 2014; 2024 replaces 2022
    rels = [_replaces(doc_2022, doc_2014), _replaces(doc_2024, doc_2022)]
    ctx = _ctx([doc_2014, doc_2022, doc_2024], rels)

    await TimelineProcessor().process(ctx)

    assert len(ctx.timeline) == 3
    assert ctx.timeline[0].document_id == doc_2014.id
    assert ctx.timeline[1].document_id == doc_2022.id
    assert ctx.timeline[2].document_id == doc_2024.id
    assert ctx.timeline[2].is_current is True
    assert ctx.timeline[0].is_current is False


@pytest.mark.asyncio
async def test_current_doc_flagged() -> None:
    doc_old = _doc("01/2014")
    doc_new = _doc("18/2024")
    rels = [_replaces(doc_new, doc_old)]
    ctx = _ctx([doc_old, doc_new], rels)

    await TimelineProcessor().process(ctx)

    current_entries = [e for e in ctx.timeline if e.is_current]
    assert len(current_entries) == 1
    assert current_entries[0].document_id == doc_new.id


@pytest.mark.asyncio
async def test_no_replaces_no_timeline() -> None:
    doc = _doc("01/2014")
    rel = DocumentRelation(
        id=uuid4(),
        source_doc_id=doc.id,
        target_doc_id=uuid4(),
        relation_type=RelationType.REFERENCES,
        created_at=datetime.now(UTC),
    )
    ctx = _ctx([doc], [rel])
    await TimelineProcessor().process(ctx)
    assert ctx.timeline == []


@pytest.mark.asyncio
async def test_disabled_processor_skips() -> None:
    doc_old = _doc("01/2014")
    doc_new = _doc("18/2024")
    rels = [_replaces(doc_new, doc_old)]
    ctx = _ctx([doc_old, doc_new], rels)

    await TimelineProcessor(enabled=False).process(ctx)
    assert ctx.timeline == []


@pytest.mark.asyncio
async def test_statistics_updated() -> None:
    doc_old = _doc("01/2014")
    doc_new = _doc("18/2024")
    rels = [_replaces(doc_new, doc_old)]
    ctx = _ctx([doc_old, doc_new], rels)

    await TimelineProcessor().process(ctx)
    assert ctx.statistics["timeline_entries"] == 2
