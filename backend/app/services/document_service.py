"""DocumentService — from application/services/document_service.py."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog

from app.core.config import settings
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.models.entities import Document
from app.models.enums import DocumentStatus, DocumentType
from app.repositories.document_store import PgDocumentRepository

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_SAFE_FILENAME_RE = re.compile(r"[^\w\-.]")


def _sanitize_filename(filename: str) -> str:
    return _SAFE_FILENAME_RE.sub("_", filename)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class DocumentService:
    def __init__(
        self,
        document_repo: PgDocumentRepository,
        storage: Any,
    ) -> None:
        self._repo = document_repo
        self._storage = storage

    async def upload_document(
        self,
        file_data: bytes,
        original_filename: str,
        content_type: str,
        dto: Any,
    ) -> Document:
        if len(file_data) > settings.max_upload_size_bytes:
            raise ValidationException(
                f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB"
            )

        if content_type not in settings.ALLOWED_CONTENT_TYPES:
            raise ValidationException(
                f"Content type '{content_type}' is not allowed. "
                f"Allowed types: {', '.join(settings.ALLOWED_CONTENT_TYPES)}"
            )

        checksum = hashlib.sha256(file_data).hexdigest()

        existing = await self._repo.get_by_checksum(checksum)
        if existing is not None:
            raise ConflictException(
                f"A document with the same content already exists (id={existing.id})"
            )

        storage_path = await self._storage.save(file_data, original_filename)

        now = datetime.now(UTC)
        document = Document(
            id=_new_uuid(),
            title=dto.title,
            filename=_sanitize_filename(original_filename),
            original_filename=original_filename,
            content_type=content_type,
            file_size=len(file_data),
            file_path=storage_path,
            content_hash=checksum,
            status=DocumentStatus.UPLOADED,
            version=1,
            doc_type=dto.doc_type,
            authority_level=dto.authority_level,
            created_at=now,
            updated_at=now,
            doc_number=dto.doc_number,
            issuing_body=dto.issuing_body,
            issued_date=dto.issued_date,
            effective_date=dto.effective_date,
            expired_date=dto.expired_date,
            tags=dto.tags,
            metadata_extra=dto.metadata_extra,
        )

        created = await self._repo.create(document)
        logger.info(
            "document_uploaded", document_id=str(created.id), filename=original_filename
        )
        return created

    async def get_document(self, document_id: UUID) -> Document:
        document = await self._repo.get_by_id(document_id)
        if document is None or document.is_deleted:
            raise NotFoundException(f"Document '{document_id}' not found")
        return document

    async def list_documents(
        self,
        offset: int,
        limit: int,
        status: DocumentStatus | None = None,
        doc_type: DocumentType | None = None,
        search: str | None = None,
    ) -> tuple[list[Document], int]:
        return await self._repo.list(
            offset=offset,
            limit=limit,
            status=status,
            doc_type=doc_type,
            search=search,
        )

    async def update_document(self, document_id: UUID, dto: Any) -> Document:
        document = await self._repo.get_by_id(document_id)
        if document is None or document.is_deleted:
            raise NotFoundException(f"Document '{document_id}' not found")

        if dto.status is not None and dto.status != document.status:
            document.transition_to(dto.status)

        if dto.title is not None:
            document.title = dto.title
        if dto.doc_number is not None:
            document.doc_number = dto.doc_number
        if dto.doc_type is not None:
            document.doc_type = dto.doc_type
        if dto.authority_level is not None:
            document.authority_level = dto.authority_level
        if dto.issuing_body is not None:
            document.issuing_body = dto.issuing_body
        if dto.issued_date is not None:
            document.issued_date = dto.issued_date
        if dto.effective_date is not None:
            document.effective_date = dto.effective_date
        if dto.expired_date is not None:
            document.expired_date = dto.expired_date
        if dto.tags is not None:
            document.tags = dto.tags
        if dto.metadata_extra is not None:
            document.metadata_extra = dto.metadata_extra

        document.increment_version()
        document.updated_at = datetime.now(UTC)

        updated = await self._repo.update(document)
        logger.info(
            "document_updated", document_id=str(updated.id), version=updated.version
        )
        return updated

    async def delete_document(self, document_id: UUID) -> None:
        document = await self._repo.get_by_id(document_id)
        if document is None or document.is_deleted:
            raise NotFoundException(f"Document '{document_id}' not found")

        now = datetime.now(UTC)
        document.soft_delete(now)
        await self._repo.soft_delete(document_id, now)

        try:
            await self._storage.delete(document.file_path)
        except Exception:
            logger.warning("storage_delete_failed", document_id=str(document_id))

        logger.info("document_deleted", document_id=str(document_id))
