"""Unit tests for DocumentRelationService helper methods.

These tests cover the pure helper methods (no DB needed):
  - apply_amendment
  - apply_partial_supersession
  - detect_conflicts
"""

from unittest.mock import AsyncMock
from uuid import UUID

from app.models.enums import SearchResult
from app.services.document_relation_service import DocumentRelationService

_DOC_A = UUID("00000000-0000-0000-0000-000000000001")
_DOC_B = UUID("00000000-0000-0000-0000-000000000002")
_CHUNK_1 = UUID("10000000-0000-0000-0000-000000000001")
_CHUNK_2 = UUID("10000000-0000-0000-0000-000000000002")


def _make_service() -> DocumentRelationService:
    """Create a DocumentRelationService with a mock session (DB not used by helper methods)."""
    mock_session = AsyncMock()
    return DocumentRelationService(session=mock_session)


def _chunk(
    chunk_id: UUID = _CHUNK_1,
    doc_id: UUID = _DOC_A,
    content: str = "nội dung mẫu",
    score: float = 0.9,
    section_title: str | None = None,
    metadata: dict | None = None,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=doc_id,
        content=content,
        score=score,
        retrieval_method="vector",
        section_title=section_title,
        metadata=metadata or {},
    )


def test_amendment_keeps_highest_score_per_document():
    """apply_amendment should keep only the highest-scored chunk per document_id."""
    service = _make_service()
    old = _chunk(chunk_id=_CHUNK_1, doc_id=_DOC_A, score=0.5)
    new = _chunk(chunk_id=_CHUNK_2, doc_id=_DOC_A, score=0.9)

    kept = service.apply_amendment([old, new])

    assert len(kept) == 1
    assert kept[0].score == 0.9


def test_amendment_keeps_separate_documents():
    """apply_amendment should keep one chunk per unique document_id."""
    service = _make_service()
    chunk_a = _chunk(chunk_id=_CHUNK_1, doc_id=_DOC_A, score=0.8)
    chunk_b = _chunk(chunk_id=_CHUNK_2, doc_id=_DOC_B, score=0.7)

    kept = service.apply_amendment([chunk_a, chunk_b])

    assert len(kept) == 2


def test_partial_supersession_drops_superseded_chunks():
    """apply_partial_supersession should remove chunks with metadata['superseded']=True."""
    service = _make_service()
    expired = _chunk(chunk_id=_CHUNK_1, doc_id=_DOC_A, metadata={"superseded": True})
    active = _chunk(chunk_id=_CHUNK_2, doc_id=_DOC_B, metadata={"superseded": False})

    kept = service.apply_partial_supersession([expired, active])

    assert kept == [active]


def test_partial_supersession_keeps_all_if_no_superseded():
    """apply_partial_supersession should keep all chunks when none are superseded."""
    service = _make_service()
    a = _chunk(chunk_id=_CHUNK_1, doc_id=_DOC_A)
    b = _chunk(chunk_id=_CHUNK_2, doc_id=_DOC_B)

    kept = service.apply_partial_supersession([a, b])

    assert len(kept) == 2


def test_detect_conflicts_flags_same_section_different_content():
    """detect_conflicts flags chunks from different docs with same section, different content."""
    service = _make_service()
    a = _chunk(
        chunk_id=_CHUNK_1,
        doc_id=_DOC_A,
        content="Lãi suất 6 tháng là 5.5%",
        section_title="Điều 1. Lãi suất",
    )
    b = _chunk(
        chunk_id=_CHUNK_2,
        doc_id=_DOC_B,
        content="Lãi suất 6 tháng là 6.0%",
        section_title="Điều 1. Lãi suất",
    )

    conflicts = service.detect_conflicts([a, b])

    assert len(conflicts) == 1
    assert conflicts[0].source_doc_id == _DOC_A
    assert conflicts[0].target_doc_id == _DOC_B


def test_detect_conflicts_no_conflict_same_document():
    """detect_conflicts should not flag chunks from the same document."""
    service = _make_service()
    a = _chunk(
        chunk_id=_CHUNK_1, doc_id=_DOC_A, content="text A", section_title="Điều 1"
    )
    b = _chunk(
        chunk_id=_CHUNK_2, doc_id=_DOC_A, content="text B", section_title="Điều 1"
    )

    conflicts = service.detect_conflicts([a, b])

    assert conflicts == []


def test_detect_conflicts_no_conflict_no_section_title():
    """detect_conflicts should not flag chunks without section_title."""
    service = _make_service()
    a = _chunk(chunk_id=_CHUNK_1, doc_id=_DOC_A, content="Lãi suất là 5.5%")
    b = _chunk(chunk_id=_CHUNK_2, doc_id=_DOC_B, content="Lãi suất là 6.0%")

    conflicts = service.detect_conflicts([a, b])

    assert conflicts == []
