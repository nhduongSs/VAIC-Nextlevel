from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.relation import DocumentRelation


class DocumentRelationRepository(ABC):
    @abstractmethod
    async def bulk_insert(self, relations: list[DocumentRelation]) -> list[DocumentRelation]: ...

    @abstractmethod
    async def get_by_document(self, document_id: UUID) -> list[DocumentRelation]: ...

    @abstractmethod
    async def delete_by_document(self, document_id: UUID) -> None: ...
