"""PgDocumentRelationRepository — from infrastructure/database/repositories/pg_relation_repo.py."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import DocumentRelation
from app.models.enums import RelationType
from app.models.orm import DocumentRelationModel


class PgDocumentRelationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: DocumentRelationModel) -> DocumentRelation:
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

    def _to_model(self, entity: DocumentRelation) -> DocumentRelationModel:
        return DocumentRelationModel(
            id=entity.id,
            source_doc_id=entity.source_doc_id,
            target_doc_id=entity.target_doc_id,
            relation_type=entity.relation_type.value,
            description=entity.description,
            confidence=entity.confidence,
            metadata_extra=entity.metadata_extra,
        )

    async def bulk_insert(
        self, relations: list[DocumentRelation]
    ) -> list[DocumentRelation]:
        models = [self._to_model(r) for r in relations]
        self._session.add_all(models)
        await self._session.flush()
        return [self._to_entity(m) for m in models]

    async def get_by_document(self, document_id: uuid.UUID) -> list[DocumentRelation]:
        stmt = select(DocumentRelationModel).where(
            (DocumentRelationModel.source_doc_id == document_id)
            | (DocumentRelationModel.target_doc_id == document_id)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete_by_document(self, document_id: uuid.UUID) -> None:
        stmt = delete(DocumentRelationModel).where(
            (DocumentRelationModel.source_doc_id == document_id)
            | (DocumentRelationModel.target_doc_id == document_id)
        )
        await self._session.execute(stmt)
        await self._session.flush()
