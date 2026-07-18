from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.domain.value_objects.chunk_type import ChunkType


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
