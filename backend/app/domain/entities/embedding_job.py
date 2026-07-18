from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.domain.value_objects.embedding_status import EmbeddingStatus


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
