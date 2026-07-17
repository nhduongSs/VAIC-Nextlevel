from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)
EntityT = TypeVar("EntityT")


class BaseRepository(ABC, Generic[ModelT, EntityT]):
    """
    Abstract base for all repository implementations.

    Subclasses provide model_class and implement _to_entity / _to_model
    mapping between SQLAlchemy models and domain entities.
    """

    model_class: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    def _to_entity(self, model: ModelT) -> EntityT:
        """Convert ORM model to domain entity."""

    @abstractmethod
    def _to_model(self, entity: EntityT) -> ModelT:
        """Convert domain entity to ORM model."""

    async def _get_model_by_id(self, entity_id: UUID) -> ModelT | None:
        return await self._session.get(self.model_class, entity_id)

    async def _execute_query(self, query: Any) -> Any:
        result = await self._session.execute(query)
        return result

    async def _count(self, stmt: Any) -> int:
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() or 0
