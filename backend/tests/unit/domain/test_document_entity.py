import uuid
from datetime import UTC, datetime

import pytest

from app.domain.entities.document import Document
from app.domain.exceptions import InvalidDocumentStatus
from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType


def _make_document(status: DocumentStatus = DocumentStatus.UPLOADED) -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid.uuid4(),
        title="Thông tư 48/2024/TT-NHNN",
        filename="thong_tu_48_2024.docx",
        original_filename="Thông tư 48/2024/TT-NHNN.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size=1024 * 512,
        file_path="ab/abcdef1234.docx",
        content_hash="a" * 64,
        status=status,
        version=1,
        doc_type=DocumentType.CIRCULAR,
        authority_level=AuthorityLevel.NHNN_CIRCULAR,
        created_at=now,
        updated_at=now,
    )


def test_initial_status_is_uploaded() -> None:
    doc = _make_document()
    assert doc.status == DocumentStatus.UPLOADED


def test_transition_uploaded_to_processing() -> None:
    doc = _make_document(DocumentStatus.UPLOADED)
    doc.transition_to(DocumentStatus.PROCESSING)
    assert doc.status == DocumentStatus.PROCESSING


def test_transition_processing_to_ready() -> None:
    doc = _make_document(DocumentStatus.PROCESSING)
    doc.transition_to(DocumentStatus.READY)
    assert doc.status == DocumentStatus.READY


def test_transition_processing_to_failed() -> None:
    doc = _make_document(DocumentStatus.PROCESSING)
    doc.transition_to(DocumentStatus.FAILED)
    assert doc.status == DocumentStatus.FAILED


def test_transition_failed_to_uploaded() -> None:
    doc = _make_document(DocumentStatus.FAILED)
    doc.transition_to(DocumentStatus.UPLOADED)
    assert doc.status == DocumentStatus.UPLOADED


def test_transition_ready_to_archived() -> None:
    doc = _make_document(DocumentStatus.READY)
    doc.transition_to(DocumentStatus.ARCHIVED)
    assert doc.status == DocumentStatus.ARCHIVED


def test_invalid_transition_raises() -> None:
    doc = _make_document(DocumentStatus.READY)
    with pytest.raises(InvalidDocumentStatus):
        doc.transition_to(DocumentStatus.UPLOADED)


def test_invalid_transition_archived_is_terminal() -> None:
    doc = _make_document(DocumentStatus.ARCHIVED)
    with pytest.raises(InvalidDocumentStatus):
        doc.transition_to(DocumentStatus.READY)


def test_increment_version() -> None:
    doc = _make_document()
    assert doc.version == 1
    doc.increment_version()
    assert doc.version == 2


def test_soft_delete() -> None:
    doc = _make_document()
    assert not doc.is_deleted
    now = datetime.now(UTC)
    doc.soft_delete(now)
    assert doc.is_deleted
    assert doc.deleted_at == now


def test_is_ready_property() -> None:
    doc = _make_document(DocumentStatus.READY)
    assert doc.is_ready

    doc.transition_to(DocumentStatus.ARCHIVED)
    assert not doc.is_ready


def test_document_has_tags_and_metadata() -> None:
    doc = _make_document()
    assert doc.tags == []
    assert doc.metadata_extra == {}

    doc.tags = ["nhnn", "banking"]
    doc.metadata_extra = {"year": 2024}
    assert doc.tags == ["nhnn", "banking"]
    assert doc.metadata_extra["year"] == 2024
