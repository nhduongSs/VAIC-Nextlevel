from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.domain.value_objects.ingestion_status import IngestionStatus


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
