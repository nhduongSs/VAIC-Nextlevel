import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.embedding_job import EmbeddingJob
from app.domain.repositories.embedding_job_repo import EmbeddingJobRepository
from app.domain.value_objects.embedding_status import EmbeddingStatus
from app.infrastructure.database.models.embedding_job_model import EmbeddingJobModel


class PgEmbeddingJobRepository(EmbeddingJobRepository):
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

    async def get_latest_by_document(self, document_id: uuid.UUID) -> EmbeddingJob | None:
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
