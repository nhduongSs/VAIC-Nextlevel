import uuid

from app.domain.exceptions import (
    ChunkLimitExceeded,
    DomainException,
    DuplicateEntity,
    EntityNotFound,
    InvalidDocumentStatus,
    InvalidEmbeddingDimension,
)


def test_entity_not_found_message() -> None:
    exc = EntityNotFound("Document", uuid.uuid4())
    assert "Document" in exc.message
    assert isinstance(exc, DomainException)


def test_invalid_embedding_dimension() -> None:
    exc = InvalidEmbeddingDimension(1024, 768)
    assert "1024" in exc.message
    assert "768" in exc.message
    assert exc.expected == 1024
    assert exc.actual == 768


def test_invalid_status_transition() -> None:
    exc = InvalidDocumentStatus("ARCHIVED", "ACTIVE")
    assert "ARCHIVED" in exc.message
    assert "ACTIVE" in exc.message


def test_chunk_limit_exceeded() -> None:
    exc = ChunkLimitExceeded(2000)
    assert "2000" in exc.message


def test_duplicate_entity() -> None:
    exc = DuplicateEntity("Document", "doc_number", "48/2024/TT-NHNN")
    assert "48/2024/TT-NHNN" in exc.message
