from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType


@dataclass
class CreateDocumentDTO:
    title: str
    doc_type: DocumentType
    authority_level: AuthorityLevel
    doc_number: str | None = None
    issuing_body: str | None = None
    issued_date: date | None = None
    effective_date: date | None = None
    expired_date: date | None = None
    tags: list[str] = field(default_factory=list)
    metadata_extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateDocumentDTO:
    title: str | None = None
    doc_number: str | None = None
    doc_type: DocumentType | None = None
    authority_level: AuthorityLevel | None = None
    issuing_body: str | None = None
    issued_date: date | None = None
    effective_date: date | None = None
    expired_date: date | None = None
    status: DocumentStatus | None = None
    tags: list[str] | None = None
    metadata_extra: dict[str, Any] | None = None
