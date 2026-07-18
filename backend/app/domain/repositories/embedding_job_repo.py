from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.embedding_job import EmbeddingJob
from app.domain.value_objects.embedding_status import EmbeddingStatus


class EmbeddingJobRepository(ABC):
    @abstractmethod
    async def create(self, job: EmbeddingJob) -> EmbeddingJob: ...

    @abstractmethod
    async def update(self, job: EmbeddingJob) -> EmbeddingJob: ...

    @abstractmethod
    async def get_by_id(self, job_id: UUID) -> EmbeddingJob | None: ...

    @abstractmethod
    async def get_latest_by_document(self, document_id: UUID) -> EmbeddingJob | None: ...

    @abstractmethod
    async def list_by_document(self, document_id: UUID) -> list[EmbeddingJob]: ...

    @abstractmethod
    async def list_by_status(self, status: EmbeddingStatus) -> list[EmbeddingJob]: ...
