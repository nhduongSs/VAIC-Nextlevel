"""Merged document, chunk, embedding job, and processing log repositories."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFound
from app.models.entities import (
    Chunk,
    Document,
    EmbeddingJob,
    ProcessingLog,
)
from app.models.enums import (
    AuthorityLevel,
    ChunkType,
    DocumentStatus,
    DocumentType,
    EmbeddingStatus,
    IngestionStatus,
)
from app.models.orm import (
    ChunkModel,
    DocumentModel,
    EmbeddingJobModel,
    ProcessingLogModel,
)

# ── PgDocumentRepository ──────────────────────────────────────────────────────


class PgDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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

        stmt = (
            base.order_by(DocumentModel.created_at.desc()).offset(offset).limit(limit)
        )
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


# ── PgChunkRepository ─────────────────────────────────────────────────────────


class PgChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: ChunkModel) -> Chunk:
        embedding: list[float] | None = (
            list(m.embedding) if m.embedding is not None else None
        )
        return Chunk(
            id=m.id,
            document_id=m.document_id,
            content=m.content,
            chunk_index=m.chunk_index,
            chunk_type=ChunkType(m.chunk_type),
            page_number=m.page_number,
            section_title=m.section_title,
            section_number=m.section_number,
            token_count=m.token_count,
            embedding=embedding,
            metadata_extra=dict(m.metadata_extra) if m.metadata_extra else {},
            created_at=m.created_at,
        )

    def _to_model(self, entity: Chunk) -> ChunkModel:
        return ChunkModel(
            id=entity.id,
            document_id=entity.document_id,
            content=entity.content,
            chunk_index=entity.chunk_index,
            chunk_type=entity.chunk_type.value,
            page_number=entity.page_number,
            section_title=entity.section_title,
            section_number=entity.section_number,
            token_count=entity.token_count,
            embedding=entity.embedding,
            metadata_extra=entity.metadata_extra,
        )

    async def bulk_insert(self, chunks: list[Chunk]) -> list[Chunk]:
        models = [self._to_model(c) for c in chunks]
        self._session.add_all(models)
        await self._session.flush()
        return [self._to_entity(m) for m in models]

    async def get_by_document(
        self,
        document_id: uuid.UUID,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[Chunk]:
        stmt = (
            select(ChunkModel)
            .where(ChunkModel.document_id == document_id)
            .order_by(ChunkModel.chunk_index)
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_document(self, document_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ChunkModel)
            .where(ChunkModel.document_id == document_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() or 0

    async def delete_by_document(self, document_id: uuid.UUID) -> None:
        stmt = delete(ChunkModel).where(ChunkModel.document_id == document_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def bulk_update_embeddings(
        self, updates: list[tuple[uuid.UUID, list[float]]]
    ) -> int:
        if not updates:
            return 0
        updated = 0
        for chunk_id, vector in updates:
            model = await self._session.get(ChunkModel, chunk_id)
            if model is not None:
                model.embedding = vector
                updated += 1
        await self._session.flush()
        return updated


# ── PgEmbeddingJobRepository ──────────────────────────────────────────────────


class PgEmbeddingJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: EmbeddingJobModel) -> EmbeddingJob:
        return EmbeddingJob(
            id=m.id,
            document_id=m.document_id,
            status=EmbeddingStatus(m.status),
            model_name=m.model_name,
            total_chunks=m.total_chunks,
            embedded_chunks=m.embedded_chunks,
            failed_chunks=m.failed_chunks,
            retry_count=m.retry_count,
            started_at=m.started_at,
            completed_at=m.completed_at,
            error_message=m.error_message,
            metadata_extra=dict(m.metadata_extra) if m.metadata_extra else {},
            created_at=m.created_at,
        )

    def _to_model(self, entity: EmbeddingJob) -> EmbeddingJobModel:
        return EmbeddingJobModel(
            id=entity.id,
            document_id=entity.document_id,
            status=entity.status.value,
            model_name=entity.model_name,
            total_chunks=entity.total_chunks,
            embedded_chunks=entity.embedded_chunks,
            failed_chunks=entity.failed_chunks,
            retry_count=entity.retry_count,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            error_message=entity.error_message,
            metadata_extra=entity.metadata_extra,
            created_at=entity.created_at,
        )

    async def create(self, job: EmbeddingJob) -> EmbeddingJob:
        model = self._to_model(job)
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, job: EmbeddingJob) -> EmbeddingJob:
        model = await self._session.get(EmbeddingJobModel, job.id)
        if model is None:
            raise ValueError(f"EmbeddingJob {job.id} not found")
        model.status = job.status.value
        model.total_chunks = job.total_chunks
        model.embedded_chunks = job.embedded_chunks
        model.failed_chunks = job.failed_chunks
        model.retry_count = job.retry_count
        model.started_at = job.started_at
        model.completed_at = job.completed_at
        model.error_message = job.error_message
        model.metadata_extra = job.metadata_extra
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_id(self, job_id: uuid.UUID) -> EmbeddingJob | None:
        model = await self._session.get(EmbeddingJobModel, job_id)
        return self._to_entity(model) if model else None

    async def get_latest_by_document(
        self, document_id: uuid.UUID
    ) -> EmbeddingJob | None:
        stmt = (
            select(EmbeddingJobModel)
            .where(EmbeddingJobModel.document_id == document_id)
            .order_by(EmbeddingJobModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_document(self, document_id: uuid.UUID) -> list[EmbeddingJob]:
        stmt = (
            select(EmbeddingJobModel)
            .where(EmbeddingJobModel.document_id == document_id)
            .order_by(EmbeddingJobModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_status(self, status: EmbeddingStatus) -> list[EmbeddingJob]:
        stmt = (
            select(EmbeddingJobModel)
            .where(EmbeddingJobModel.status == status.value)
            .order_by(EmbeddingJobModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]


# ── PgProcessingLogRepository ─────────────────────────────────────────────────


class PgProcessingLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: ProcessingLogModel) -> ProcessingLog:
        return ProcessingLog(
            id=m.id,
            document_id=m.document_id,
            status=IngestionStatus(m.status),
            started_at=m.started_at,
            completed_at=m.completed_at,
            current_stage=m.current_stage,
            error_message=m.error_message,
            stage_results=dict(m.stage_results) if m.stage_results else {},
            retry_count=m.retry_count,
            created_at=m.created_at,
        )

    def _to_model(self, entity: ProcessingLog) -> ProcessingLogModel:
        return ProcessingLogModel(
            id=entity.id,
            document_id=entity.document_id,
            status=entity.status.value,
            current_stage=entity.current_stage,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            error_message=entity.error_message,
            stage_results=entity.stage_results,
            retry_count=entity.retry_count,
        )

    async def create(self, log: ProcessingLog) -> ProcessingLog:
        model = self._to_model(log)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def update(self, log: ProcessingLog) -> ProcessingLog:
        model = await self._session.get(ProcessingLogModel, log.id)
        if model is None:
            raise EntityNotFound("ProcessingLog", log.id)
        model.status = log.status.value
        model.current_stage = log.current_stage
        model.completed_at = log.completed_at
        model.error_message = log.error_message
        model.stage_results = log.stage_results
        model.retry_count = log.retry_count
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_latest_by_document(
        self, document_id: uuid.UUID
    ) -> ProcessingLog | None:
        stmt = (
            select(ProcessingLogModel)
            .where(ProcessingLogModel.document_id == document_id)
            .order_by(ProcessingLogModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model is not None else None

    async def list_by_document(self, document_id: uuid.UUID) -> list[ProcessingLog]:
        stmt = (
            select(ProcessingLogModel)
            .where(ProcessingLogModel.document_id == document_id)
            .order_by(ProcessingLogModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]
