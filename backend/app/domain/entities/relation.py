from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.domain.value_objects.relation_type import RelationType


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
