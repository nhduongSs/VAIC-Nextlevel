"""Shared ORM → domain entity mappers for the Knowledge Intelligence layer."""

from __future__ import annotations

from app.domain.entities.document import Document
from app.domain.entities.relation import DocumentRelation
from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType
from app.domain.value_objects.relation_type import RelationType
from app.infrastructure.database.models.document_model import DocumentModel
from app.infrastructure.database.models.relation_model import DocumentRelationModel


def document_to_entity(m: DocumentModel) -> Document:
    return Document(
        id=m.id,
        title=m.title,
        filename=m.filename,
        original_filename=m.original_filename,
        content_type=m.content_type,
        file_size=m.file_size,
        file_path=m.file_path,
        content_hash=m.content_hash,
        status=DocumentStatus(m.status),
        version=m.version,
        doc_type=DocumentType(m.doc_type),
        authority_level=AuthorityLevel(m.authority_level),
        created_at=m.created_at,
        updated_at=m.updated_at,
        doc_number=m.doc_number,
        issuing_body=m.issuing_body,
        issued_date=m.issued_date,
        effective_date=m.effective_date,
        expired_date=m.expired_date,
        tags=list(m.tags) if m.tags else [],
        metadata_extra=dict(m.metadata_extra) if m.metadata_extra else {},
        deleted_at=m.deleted_at,
    )


def relation_to_entity(m: DocumentRelationModel) -> DocumentRelation:
    return DocumentRelation(
        id=m.id,
        source_doc_id=m.source_doc_id,
        target_doc_id=m.target_doc_id,
        relation_type=RelationType(m.relation_type),
        confidence=m.confidence,
        description=m.description,
        metadata_extra=dict(m.metadata_extra) if m.metadata_extra else {},
        created_at=m.created_at,
    )
