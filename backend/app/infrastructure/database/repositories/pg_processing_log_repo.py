import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.processing_log import ProcessingLog
from app.domain.exceptions import EntityNotFound
from app.domain.repositories.processing_log_repo import ProcessingLogRepository
from app.domain.value_objects.ingestion_status import IngestionStatus
from app.infrastructure.database.models.processing_log_model import ProcessingLogModel


class PgProcessingLogRepository(ProcessingLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Mapping ──────────────────────────────────────────────────────────────

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

    # ── Repository methods ────────────────────────────────────────────────────

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

    async def get_latest_by_document(self, document_id: uuid.UUID) -> ProcessingLog | None:
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
