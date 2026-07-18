from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, ClassVar
from uuid import UUID

from app.domain.exceptions import InvalidDocumentStatus
from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType


@dataclass
class Document:
    id: UUID
    title: str
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    file_path: str
    content_hash: str
    status: DocumentStatus
    version: int
    doc_type: DocumentType
    authority_level: AuthorityLevel
    created_at: datetime
    updated_at: datetime
    doc_number: str | None = None
    issuing_body: str | None = None
    issued_date: date | None = None
    effective_date: date | None = None
    expired_date: date | None = None
    tags: list[str] = field(default_factory=list)
    metadata_extra: dict[str, Any] = field(default_factory=dict)
    deleted_at: datetime | None = None

    _VALID_TRANSITIONS: ClassVar[dict[DocumentStatus, frozenset[DocumentStatus]]] = {
        DocumentStatus.UPLOADED: frozenset(
            {DocumentStatus.PROCESSING, DocumentStatus.FAILED, DocumentStatus.ARCHIVED}
        ),
        DocumentStatus.PROCESSING: frozenset({DocumentStatus.READY, DocumentStatus.FAILED}),
        DocumentStatus.READY: frozenset({DocumentStatus.ARCHIVED}),
        DocumentStatus.FAILED: frozenset(
            {DocumentStatus.UPLOADED, DocumentStatus.PROCESSING, DocumentStatus.ARCHIVED}
        ),
        DocumentStatus.ARCHIVED: frozenset(),
    }

    def transition_to(self, new_status: DocumentStatus) -> None:
        allowed = self._VALID_TRANSITIONS.get(self.status, frozenset())
        if new_status not in allowed:
            raise InvalidDocumentStatus(self.status.value, new_status.value)
        self.status = new_status

    def increment_version(self) -> None:
        self.version += 1

    def soft_delete(self, now: datetime) -> None:
        self.deleted_at = now

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_ready(self) -> bool:
        return self.status == DocumentStatus.READY and not self.is_deleted
