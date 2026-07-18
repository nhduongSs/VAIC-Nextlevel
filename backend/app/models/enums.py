"""All enums and value objects collected from domain/value_objects/."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID


class DocumentType(StrEnum):
    LAW = "LAW"
    CIRCULAR = "CIRCULAR"
    DECREE = "DECREE"
    DECISION = "DECISION"
    POLICY = "POLICY"
    SOP = "SOP"
    FAQ = "FAQ"
    PRODUCT_DOC = "PRODUCT_DOC"
    MANUAL = "MANUAL"
    UNKNOWN = "UNKNOWN"


class AuthorityLevel(StrEnum):
    NATIONAL_LAW = "NATIONAL_LAW"
    NHNN_CIRCULAR = "NHNN_CIRCULAR"
    NHNN_DECISION = "NHNN_DECISION"
    INTERNAL_POLICY = "INTERNAL_POLICY"
    DEPARTMENT_SOP = "DEPARTMENT_SOP"
    FAQ = "FAQ"
    UNKNOWN = "UNKNOWN"


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class ChunkType(StrEnum):
    ARTICLE = "ARTICLE"
    CLAUSE = "CLAUSE"
    PARAGRAPH = "PARAGRAPH"
    TABLE = "TABLE"
    DEFINITION = "DEFINITION"
    APPENDIX = "APPENDIX"


class EmbeddingStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


class IngestionStatus(StrEnum):
    QUEUED = "QUEUED"
    PARSING = "PARSING"
    EXTRACTING_METADATA = "EXTRACTING_METADATA"
    CLASSIFYING = "CLASSIFYING"
    EXTRACTING_RELATIONSHIPS = "EXTRACTING_RELATIONSHIPS"
    CHUNKING = "CHUNKING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RelationType(StrEnum):
    REPLACES = "REPLACES"
    AMENDS = "AMENDS"
    REFERENCES = "REFERENCES"
    SUPPLEMENTS = "SUPPLEMENTS"
    IMPLEMENTS = "IMPLEMENTS"
    CONFLICTS_WITH = "CONFLICTS_WITH"


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
