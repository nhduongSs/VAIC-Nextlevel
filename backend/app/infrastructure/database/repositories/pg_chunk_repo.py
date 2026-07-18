import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.chunk import Chunk
from app.domain.repositories.chunk_repo import ChunkRepository
from app.domain.value_objects.chunk_type import ChunkType
from app.infrastructure.database.models.chunk_model import ChunkModel


class PgChunkRepository(ChunkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Mapping ──────────────────────────────────────────────────────────────

    def _to_entity(self, m: ChunkModel) -> Chunk:
        embedding: list[float] | None = list(m.embedding) if m.embedding is not None else None
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

    # ── Repository methods ────────────────────────────────────────────────────

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

    async def bulk_update_embeddings(self, updates: list[tuple[uuid.UUID, list[float]]]) -> int:
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
