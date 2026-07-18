from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.processing_log import ProcessingLog


class ProcessingLogRepository(ABC):
    @abstractmethod
    async def create(self, log: ProcessingLog) -> ProcessingLog: ...

    @abstractmethod
    async def update(self, log: ProcessingLog) -> ProcessingLog: ...

    @abstractmethod
    async def get_latest_by_document(self, document_id: UUID) -> ProcessingLog | None: ...

    @abstractmethod
    async def list_by_document(self, document_id: UUID) -> list[ProcessingLog]: ...
