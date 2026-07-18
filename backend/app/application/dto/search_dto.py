from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID


@dataclass
class SearchFilters:
    doc_type: str | None = None
    authority_level: str | None = None
    department: str | None = None
    language: str | None = None
    version: int | None = None
    effective_date_from: date | None = None
    effective_date_to: date | None = None
    tags: list[str] = field(default_factory=list)
    document_ids: list[UUID] = field(default_factory=list)


@dataclass
class SearchRequest:
    query: str
    top_k: int = 10
    filters: SearchFilters | None = None
    vector_weight: float | None = None  # override SEARCH_HYBRID_ALPHA
    bm25_weight: float | None = None  # override SEARCH_HYBRID_BETA
