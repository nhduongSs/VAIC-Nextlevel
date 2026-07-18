"""Domain entities collected from domain/entities/."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, ClassVar
from uuid import UUID

from app.core.exceptions import InvalidDocumentStatus
from app.models.enums import (
    AuthorityLevel,
    ChunkType,
    DocumentStatus,
    DocumentType,
    EmbeddingStatus,
    IngestionStatus,
    RelationType,
)


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
        DocumentStatus.PROCESSING: frozenset(
            {DocumentStatus.READY, DocumentStatus.FAILED}
        ),
        DocumentStatus.READY: frozenset({DocumentStatus.ARCHIVED}),
        DocumentStatus.FAILED: frozenset(
            {
                DocumentStatus.UPLOADED,
                DocumentStatus.PROCESSING,
                DocumentStatus.ARCHIVED,
            }
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


@dataclass
class Chunk:
    id: UUID
    document_id: UUID
    content: str
    chunk_index: int
    chunk_type: ChunkType
    page_number: int | None = None
    section_title: str | None = None
    section_number: str | None = None
    token_count: int | None = None
    embedding: list[float] | None = None
    metadata_extra: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_context_string(self) -> str:
        parts: list[str] = []
        if self.section_number:
            parts.append(self.section_number)
        if self.section_title:
            parts.append(self.section_title)
        parts.append(self.content)
        return "\n".join(parts)


@dataclass
class DocumentRelation:
    id: UUID
    source_doc_id: UUID
    target_doc_id: UUID
    relation_type: RelationType
    confidence: float = 1.0
    description: str | None = None
    metadata_extra: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_supersession(self) -> bool:
        return self.relation_type == RelationType.REPLACES

    def is_amendment(self) -> bool:
        return self.relation_type == RelationType.AMENDS


@dataclass
class EmbeddingJob:
    id: UUID
    document_id: UUID
    status: EmbeddingStatus
    model_name: str
    total_chunks: int = 0
    embedded_chunks: int = 0
    failed_chunks: int = 0
    retry_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    metadata_extra: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            EmbeddingStatus.COMPLETED,
            EmbeddingStatus.FAILED,
            EmbeddingStatus.CANCELLED,
        )

    @property
    def progress_pct(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return round(self.embedded_chunks / self.total_chunks * 100, 1)

    def start(self) -> None:
        self.status = EmbeddingStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def complete(self) -> None:
        self.status = EmbeddingStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

    def fail(self, error: str) -> None:
        self.status = EmbeddingStatus.FAILED
        self.completed_at = datetime.now(UTC)
        self.error_message = error

    def mark_retrying(self) -> None:
        self.status = EmbeddingStatus.RETRYING
        self.retry_count += 1


@dataclass
class ProcessingLog:
    id: UUID
    document_id: UUID
    status: IngestionStatus
    started_at: datetime
    completed_at: datetime | None = None
    current_stage: str | None = None
    error_message: str | None = None
    stage_results: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_terminal(self) -> bool:
        return self.status in (IngestionStatus.COMPLETED, IngestionStatus.FAILED)

    def mark_stage(self, stage: IngestionStatus) -> None:
        self.status = stage
        self.current_stage = stage.value

    def complete(self, stage_results: dict[str, Any] | None = None) -> None:
        self.status = IngestionStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        if stage_results:
            self.stage_results = stage_results

    def fail(self, error_message: str) -> None:
        self.status = IngestionStatus.FAILED
        self.completed_at = datetime.now(UTC)
        self.error_message = error_message
