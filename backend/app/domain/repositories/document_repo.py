from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.entities.document import Document
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType


class DocumentRepository(ABC):
    @abstractmethod
    async def create(self, document: Document) -> Document: ...

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> Document | None: ...

    @abstractmethod
    async def update(self, document: Document) -> Document: ...

    @abstractmethod
    async def soft_delete(self, document_id: UUID, deleted_at: datetime) -> None: ...

    @abstractmethod
    async def list(
        self,
        offset: int,
        limit: int,
        status: DocumentStatus | None = None,
        doc_type: DocumentType | None = None,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[Document], int]: ...

    @abstractmethod
    async def get_by_checksum(self, checksum: str) -> Document | None: ...
