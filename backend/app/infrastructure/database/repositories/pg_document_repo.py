import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.document import Document
from app.domain.exceptions import EntityNotFound
from app.domain.repositories.document_repo import DocumentRepository
from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType
from app.infrastructure.database.base_repository import BaseRepository
from app.infrastructure.database.models.document_model import DocumentModel


class PgDocumentRepository(BaseRepository[DocumentModel, Document], DocumentRepository):
    model_class = DocumentModel

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ── Mapping ──────────────────────────────────────────────────────────────

    def _to_entity(self, model: DocumentModel) -> Document:
        return Document(
            id=model.id,
            title=model.title,
            filename=model.filename,
            original_filename=model.original_filename,
            content_type=model.content_type,
            file_size=model.file_size,
            file_path=model.file_path,
            content_hash=model.content_hash,
            status=DocumentStatus(model.status),
            version=model.version,
            doc_type=DocumentType(model.doc_type),
            authority_level=AuthorityLevel(model.authority_level),
            created_at=model.created_at,
            updated_at=model.updated_at,
            doc_number=model.doc_number,
            issuing_body=model.issuing_body,
            issued_date=model.issued_date,
            effective_date=model.effective_date,
            expired_date=model.expired_date,
            tags=list(model.tags) if model.tags else [],
            metadata_extra=dict(model.metadata_extra) if model.metadata_extra else {},
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Document) -> DocumentModel:
        return DocumentModel(
            id=entity.id,
            title=entity.title,
            filename=entity.filename,
            original_filename=entity.original_filename,
            content_type=entity.content_type,
            file_size=entity.file_size,
            file_path=entity.file_path,
            content_hash=entity.content_hash,
            status=entity.status.value,
            version=entity.version,
            doc_type=entity.doc_type.value,
            authority_level=entity.authority_level.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            doc_number=entity.doc_number,
            issuing_body=entity.issuing_body,
            issued_date=entity.issued_date,
            effective_date=entity.effective_date,
            expired_date=entity.expired_date,
            tags=entity.tags,
            metadata_extra=entity.metadata_extra,
            deleted_at=entity.deleted_at,
        )

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, document: Document) -> Document:
        model = self._to_model(document)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        model = await self._session.get(DocumentModel, document_id)
        return self._to_entity(model) if model is not None else None

    async def update(self, document: Document) -> Document:
        model = await self._session.get(DocumentModel, document.id)
        if model is None:
            raise EntityNotFound("Document", document.id)
        model.title = document.title
        model.doc_number = document.doc_number
        model.doc_type = document.doc_type.value
        model.authority_level = document.authority_level.value
        model.status = document.status.value
        model.version = document.version
        model.issuing_body = document.issuing_body
        model.issued_date = document.issued_date
        model.effective_date = document.effective_date
        model.expired_date = document.expired_date
        model.tags = document.tags
        model.metadata_extra = document.metadata_extra
        model.updated_at = document.updated_at
        model.deleted_at = document.deleted_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def soft_delete(self, document_id: uuid.UUID, deleted_at: datetime) -> None:
        model = await self._session.get(DocumentModel, document_id)
        if model is None:
            raise EntityNotFound("Document", document_id)
        model.deleted_at = deleted_at
        await self._session.flush()

    async def list(
        self,
        offset: int,
        limit: int,
        status: DocumentStatus | None = None,
        doc_type: DocumentType | None = None,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[Document], int]:
        base = select(DocumentModel)
        count_base = select(func.count()).select_from(DocumentModel)

        filters: list[Any] = []
        if not include_deleted:
            filters.append(DocumentModel.deleted_at.is_(None))
        if status is not None:
            filters.append(DocumentModel.status == status.value)
        if doc_type is not None:
            filters.append(DocumentModel.doc_type == doc_type.value)
        if search:
            filters.append(DocumentModel.title.ilike(f"%{search}%"))

        for f in filters:
            base = base.where(f)
            count_base = count_base.where(f)

        total_result = await self._session.execute(count_base)
        total: int = total_result.scalar_one_or_none() or 0

        stmt = base.order_by(DocumentModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models], total

    async def get_by_checksum(self, checksum: str) -> Document | None:
        stmt = select(DocumentModel).where(
            DocumentModel.content_hash == checksum,
            DocumentModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model is not None else None
