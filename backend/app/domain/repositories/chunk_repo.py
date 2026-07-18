from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.chunk import Chunk


class ChunkRepository(ABC):
    @abstractmethod
    async def bulk_insert(self, chunks: list[Chunk]) -> list[Chunk]: ...

    @abstractmethod
    async def get_by_document(
        self,
        document_id: UUID,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[Chunk]: ...

    @abstractmethod
    async def count_by_document(self, document_id: UUID) -> int: ...

    @abstractmethod
    async def delete_by_document(self, document_id: UUID) -> None: ...

    @abstractmethod
    async def bulk_update_embeddings(self, updates: list[tuple[UUID, list[float]]]) -> int: ...
