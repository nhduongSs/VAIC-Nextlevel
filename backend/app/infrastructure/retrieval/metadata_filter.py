from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, cast
from sqlalchemy.dialects.postgresql import JSONB

from app.application.dto.search_dto import SearchFilters
from app.infrastructure.database.models.chunk_model import ChunkModel
from app.infrastructure.database.models.document_model import DocumentModel


class MetadataFilter:
    """Builds SQLAlchemy WHERE conditions from SearchFilters.

    All conditions target the DocumentModel joined to ChunkModel.
    """

    def build(self, filters: SearchFilters | None) -> list[ColumnElement[Any]]:
        conditions: list[ColumnElement[Any]] = [
            DocumentModel.deleted_at.is_(None),
        ]
        if filters is None:
            return conditions

        if filters.doc_type:
            conditions.append(DocumentModel.doc_type == filters.doc_type)

        if filters.authority_level:
            conditions.append(DocumentModel.authority_level == filters.authority_level)

        if filters.department:
            conditions.append(
                DocumentModel.metadata_extra["department"].astext == filters.department
            )

        if filters.language:
            conditions.append(DocumentModel.metadata_extra["language"].astext == filters.language)

        if filters.version:
            conditions.append(DocumentModel.version == filters.version)

        if filters.effective_date_from:
            conditions.append(DocumentModel.effective_date >= filters.effective_date_from)

        if filters.effective_date_to:
            conditions.append(DocumentModel.effective_date <= filters.effective_date_to)

        if filters.tags:
            for tag in filters.tags:
                conditions.append(DocumentModel.tags.op("@>")(cast([tag], JSONB)))

        if filters.document_ids:
            conditions.append(ChunkModel.document_id.in_(filters.document_ids))

        return conditions
