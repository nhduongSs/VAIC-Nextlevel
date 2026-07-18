import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.application.dto.document_dto import CreateDocumentDTO, UpdateDocumentDTO
from app.application.services.document_service import DocumentService
from app.domain.entities.document import Document
from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType
from app.presentation.exceptions import ConflictException, NotFoundException, ValidationException


def _make_entity(
    doc_id: uuid.UUID | None = None,
    status: DocumentStatus = DocumentStatus.UPLOADED,
) -> Document:
    now = datetime.now(UTC)
    return Document(
        id=doc_id or uuid.uuid4(),
        title="Test Document",
        filename="test.docx",
        original_filename="test.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size=1024,
        file_path="ab/abcd1234.docx",
        content_hash="b" * 64,
        status=status,
        version=1,
        doc_type=DocumentType.CIRCULAR,
        authority_level=AuthorityLevel.NHNN_CIRCULAR,
        created_at=now,
        updated_at=now,
    )


def _make_service(
    repo: AsyncMock | None = None,
    storage: AsyncMock | None = None,
) -> DocumentService:
    if repo is None:
        repo = AsyncMock()
    if storage is None:
        storage = AsyncMock()
    return DocumentService(repo, storage)


def _make_dto() -> CreateDocumentDTO:
    return CreateDocumentDTO(
        title="Thông tư 48",
        doc_type=DocumentType.CIRCULAR,
        authority_level=AuthorityLevel.NHNN_CIRCULAR,
    )


# ── upload_document ───────────────────────────────────────────────────────────


async def test_upload_creates_document() -> None:
    entity = _make_entity()
    repo = AsyncMock()
    repo.get_by_checksum.return_value = None
    repo.create.return_value = entity
    storage = AsyncMock()
    storage.save.return_value = "ab/file.docx"

    service = _make_service(repo, storage)
    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    result = await service.upload_document(
        file_data=b"hello world",
        original_filename="test.docx",
        content_type=content_type,
        dto=_make_dto(),
    )

    assert result.id == entity.id
    repo.create.assert_called_once()
    storage.save.assert_called_once()


async def test_upload_rejects_duplicate_checksum() -> None:
    repo = AsyncMock()
    repo.get_by_checksum.return_value = _make_entity()

    service = _make_service(repo)
    with pytest.raises(ConflictException):
        await service.upload_document(
            file_data=b"hello",
            original_filename="test.docx",
            content_type="application/pdf",
            dto=_make_dto(),
        )


async def test_upload_rejects_oversized_file() -> None:
    repo = AsyncMock()
    repo.get_by_checksum.return_value = None

    service = _make_service(repo)
    big_file = b"x" * (51 * 1024 * 1024)  # 51 MB

    with pytest.raises(ValidationException, match="size"):
        await service.upload_document(
            file_data=big_file,
            original_filename="big.pdf",
            content_type="application/pdf",
            dto=_make_dto(),
        )


async def test_upload_rejects_invalid_content_type() -> None:
    repo = AsyncMock()
    repo.get_by_checksum.return_value = None

    service = _make_service(repo)
    with pytest.raises(ValidationException, match="Content type"):
        await service.upload_document(
            file_data=b"data",
            original_filename="evil.exe",
            content_type="application/x-msdownload",
            dto=_make_dto(),
        )


# ── get_document ──────────────────────────────────────────────────────────────


async def test_get_document_returns_entity() -> None:
    entity = _make_entity()
    repo = AsyncMock()
    repo.get_by_id.return_value = entity

    service = _make_service(repo)
    result = await service.get_document(entity.id)
    assert result.id == entity.id


async def test_get_document_raises_not_found_when_missing() -> None:
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    service = _make_service(repo)
    with pytest.raises(NotFoundException):
        await service.get_document(uuid.uuid4())


async def test_get_document_raises_not_found_when_deleted() -> None:
    entity = _make_entity()
    entity.soft_delete(datetime.now(UTC))
    repo = AsyncMock()
    repo.get_by_id.return_value = entity

    service = _make_service(repo)
    with pytest.raises(NotFoundException):
        await service.get_document(entity.id)


# ── update_document ───────────────────────────────────────────────────────────


async def test_update_document_applies_dto_fields() -> None:
    entity = _make_entity()
    updated_entity = _make_entity(doc_id=entity.id)
    updated_entity.title = "Updated Title"
    updated_entity.version = 2

    repo = AsyncMock()
    repo.get_by_id.return_value = entity
    repo.update.return_value = updated_entity

    service = _make_service(repo)
    dto = UpdateDocumentDTO(title="Updated Title")
    result = await service.update_document(entity.id, dto)

    assert result.title == "Updated Title"
    repo.update.assert_called_once()


async def test_update_document_increments_version() -> None:
    entity = _make_entity()
    repo = AsyncMock()
    repo.get_by_id.return_value = entity
    repo.update.side_effect = lambda d: d

    service = _make_service(repo)
    result = await service.update_document(entity.id, UpdateDocumentDTO(title="New"))
    assert result.version == 2


async def test_update_transitions_status() -> None:
    entity = _make_entity(status=DocumentStatus.UPLOADED)
    repo = AsyncMock()
    repo.get_by_id.return_value = entity
    repo.update.side_effect = lambda d: d

    service = _make_service(repo)
    dto = UpdateDocumentDTO(status=DocumentStatus.PROCESSING)
    result = await service.update_document(entity.id, dto)
    assert result.status == DocumentStatus.PROCESSING


# ── delete_document ───────────────────────────────────────────────────────────


async def test_delete_document_soft_deletes() -> None:
    entity = _make_entity()
    repo = AsyncMock()
    repo.get_by_id.return_value = entity
    storage = AsyncMock()

    service = _make_service(repo, storage)
    await service.delete_document(entity.id)

    repo.soft_delete.assert_called_once()
    storage.delete.assert_called_once()


async def test_delete_document_raises_not_found() -> None:
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    service = _make_service(repo)
    with pytest.raises(NotFoundException):
        await service.delete_document(uuid.uuid4())
