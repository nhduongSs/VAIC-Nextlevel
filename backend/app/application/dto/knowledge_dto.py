from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID

from app.domain.entities.document import Document
from app.domain.entities.relation import DocumentRelation
from app.domain.value_objects.search_result import SearchResult


@dataclass
class Citation:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    doc_number: str | None
    section_title: str | None
    section_number: str | None
    page_number: int | None
    chunk_index: int
    authority_level: str
    version: int
    effective_date: date | None
    content_preview: str


@dataclass
class TimelineEntry:
    document_id: UUID
    document_title: str
    doc_number: str | None
    version: int
    effective_date: date | None
    issued_date: date | None
    relation_type: str | None
    is_current: bool = True


@dataclass
class ConflictInfo:
    source_doc_id: UUID
    target_doc_id: UUID
    source_title: str
    target_title: str
    description: str | None
    confidence: float


@dataclass
class ContextPackage:
    query: str
    ranked_chunks: list[SearchResult]
    citations: list[Citation]
    relationships: list[DocumentRelation]
    conflicts: list[ConflictInfo]
    timeline: list[TimelineEntry]
    metadata: dict[str, Any]
    statistics: dict[str, Any]


@dataclass
class KnowledgeContext:
    query: str
    retrieved_chunks: list[SearchResult]
    ranked_chunks: list[SearchResult]
    document_map: dict[UUID, Document]
    citations: list[Citation] = field(default_factory=list)
    relationships: list[DocumentRelation] = field(default_factory=list)
    conflicts: list[ConflictInfo] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    statistics: dict[str, Any] = field(default_factory=dict)
    context_package: ContextPackage | None = None
