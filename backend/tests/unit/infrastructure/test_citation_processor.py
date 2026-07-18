"""Unit tests for CitationProcessor."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.application.dto.knowledge_dto import KnowledgeContext
from app.domain.entities.document import Document
from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.knowledge.processors.citation_processor import CitationProcessor


def _doc(doc_number: str = "48/2024/TT-NHNN") -> Document:
    now = datetime.now(UTC)
    did = uuid4()
    return Document(
        id=did,
        title="Thông tư 48/2024",
        filename="tt48.docx",
        original_filename="tt48.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size=1000,
        file_path="uploads/tt48.docx",
        content_hash="abc123",
        status=DocumentStatus.READY,
        version=2,
        doc_type=DocumentType.CIRCULAR,
        authority_level=AuthorityLevel.NHNN_CIRCULAR,
        created_at=now,
        updated_at=now,
        doc_number=doc_number,
        effective_date=date(2024, 7, 1),
    )


def _chunk(doc: Document, content: str = "A" * 300) -> SearchResult:
    return SearchResult(
        chunk_id=uuid4(),
        document_id=doc.id,
        content=content,
        score=0.9,
        retrieval_method="hybrid",
        section_title="Điều 1",
        section_number="1",
        page_number=3,
        chunk_index=2,
    )


@pytest.mark.asyncio
async def test_citation_created_for_each_chunk() -> None:
    doc = _doc()
    chunk = _chunk(doc)
    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk],
        ranked_chunks=[chunk],
        document_map={doc.id: doc},
    )
    await CitationProcessor(max_citations=10).process(ctx)

    assert len(ctx.citations) == 1
    cit = ctx.citations[0]
    assert cit.chunk_id == chunk.chunk_id
    assert cit.document_id == doc.id
    assert cit.document_title == "Thông tư 48/2024"
    assert cit.doc_number == "48/2024/TT-NHNN"
    assert cit.section_title == "Điều 1"
    assert cit.page_number == 3
    assert cit.authority_level == "NHNN_CIRCULAR"
    assert cit.version == 2


@pytest.mark.asyncio
async def test_content_preview_truncated_to_200_chars() -> None:
    doc = _doc()
    chunk = _chunk(doc, content="X" * 500)
    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk],
        ranked_chunks=[chunk],
        document_map={doc.id: doc},
    )
    await CitationProcessor().process(ctx)
    assert len(ctx.citations[0].content_preview) == 200


@pytest.mark.asyncio
async def test_max_citations_respected() -> None:
    doc = _doc()
    chunks = [_chunk(doc) for _ in range(15)]
    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=chunks,
        ranked_chunks=chunks,
        document_map={doc.id: doc},
    )
    await CitationProcessor(max_citations=5).process(ctx)
    assert len(ctx.citations) == 5


@pytest.mark.asyncio
async def test_missing_doc_uses_fallback_values() -> None:
    missing_id = uuid4()
    chunk = SearchResult(
        chunk_id=uuid4(),
        document_id=missing_id,
        content="content",
        score=0.5,
        retrieval_method="bm25",
    )
    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk],
        ranked_chunks=[chunk],
        document_map={},
    )
    await CitationProcessor().process(ctx)
    assert ctx.citations[0].document_title == "Unknown"
    assert ctx.citations[0].authority_level == "UNKNOWN"
    assert ctx.citations[0].version == 1


@pytest.mark.asyncio
async def test_disabled_processor_skips() -> None:
    doc = _doc()
    chunk = _chunk(doc)
    ctx = KnowledgeContext(
        query="test",
        retrieved_chunks=[chunk],
        ranked_chunks=[chunk],
        document_map={doc.id: doc},
    )
    await CitationProcessor(enabled=False).process(ctx)
    assert ctx.citations == []
