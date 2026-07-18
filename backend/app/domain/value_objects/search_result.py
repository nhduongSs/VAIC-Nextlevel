from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class SearchResult:
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float
    retrieval_method: str  # "bm25" | "vector" | "hybrid"
    bm25_score: float | None = None
    vector_score: float | None = None
    chunk_index: int = 0
    chunk_type: str = ""
    section_title: str | None = None
    section_number: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
