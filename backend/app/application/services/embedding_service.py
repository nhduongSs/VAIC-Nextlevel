"""Embedding pipeline service.

Creates its own DB session (via session factory) so it is safe to call
from FastAPI BackgroundTasks after the request session has been closed.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.chunk import Chunk
from app.domain.entities.embedding_job import EmbeddingJob
from app.domain.value_objects.embedding_status import EmbeddingStatus
from app.infrastructure.ai.embedding.embedding_provider import EmbeddingProvider
from app.infrastructure.database.repositories.pg_chunk_repo import PgChunkRepository
from app.infrastructure.database.repositories.pg_embedding_job_repo import (
    PgEmbeddingJobRepository,
)
from app.utils.uuid_utils import new_uuid

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_MAX_RETRIES = 2
_RETRY_DELAY = 2.0


class EmbeddingService:
    """Embeds all chunks for a document and persists the vectors."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        provider: EmbeddingProvider,
        batch_size: int = 32,
        max_concurrency: int = 4,
        max_retries: int = _MAX_RETRIES,
        retry_delay: float = _RETRY_DELAY,
        batch_timeout: float = 120.0,
    ) -> None:
        self._session_factory = session_factory
        self._provider = provider
        self._batch_size = batch_size
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._batch_timeout = batch_timeout

    async def embed_document(self, document_id: UUID) -> None:
        """Entry point for background embedding with retry support."""
        for attempt in range(1, self._max_retries + 2):
            try:
                await self._run(document_id, retry_count=attempt - 1)
                return
            except Exception as exc:
                if attempt <= self._max_retries:
                    log.warning(
                        "embedding_retry",
                        document_id=str(document_id),
                        attempt=attempt,
                        error=str(exc),
                    )
                    await asyncio.sleep(self._retry_delay * attempt)
                else:
                    log.error(
                        "embedding_failed_permanently",
                        document_id=str(document_id),
                        error=str(exc),
                        exc_info=True,
                    )
                    await self._mark_failed(document_id, str(exc))

    async def _run(self, document_id: UUID, retry_count: int = 0) -> None:
        async with self._session_factory() as session:
            chunk_repo = PgChunkRepository(session)
            job_repo = PgEmbeddingJobRepository(session)

            # ── Load chunks ───────────────────────────────────────────────
            chunks = await chunk_repo.get_by_document(document_id)
            if not chunks:
                log.info("embedding_skipped_no_chunks", document_id=str(document_id))
                return

            # ── Create job record ─────────────────────────────────────────
            job = EmbeddingJob(
                id=new_uuid(),
                document_id=document_id,
                status=EmbeddingStatus.PENDING,
                model_name=self._provider.model_name,
                total_chunks=len(chunks),
                retry_count=retry_count,
                created_at=datetime.now(UTC),
            )
            job = await job_repo.create(job)
            await session.commit()

            job.start()
            job = await job_repo.update(job)
            await session.commit()

            bound = log.bind(
                document_id=str(document_id),
                job_id=str(job.id),
                total=len(chunks),
            )
            bound.info("embedding_started")

            # ── Batch embedding with semaphore ────────────────────────────
            batches = [
                chunks[i : i + self._batch_size] for i in range(0, len(chunks), self._batch_size)
            ]

            # Each wrapper coroutine captures its own batch size so failures are exact
            async def _safe_batch(
                batch_chunks: list[Chunk],
            ) -> tuple[list[tuple[UUID, list[float]]], int]:
                """Returns (updates, failed_count). Never raises."""
                texts = [c.content for c in batch_chunks]
                try:
                    async with self._semaphore:
                        vectors = await asyncio.wait_for(
                            self._provider.embed(texts),
                            timeout=self._batch_timeout,
                        )
                    return [(c.id, v) for c, v in zip(batch_chunks, vectors, strict=True)], 0
                except Exception as exc:
                    bound.warning("embedding_batch_failed", error=str(exc))
                    return [], len(batch_chunks)

            tasks = [asyncio.create_task(_safe_batch(b)) for b in batches]

            updates: list[tuple[UUID, list[float]]] = []
            any_failed = False
            for coro in asyncio.as_completed(tasks):
                batch_updates, failed_count = await coro
                updates.extend(batch_updates)
                job.embedded_chunks += len(batch_updates)
                if failed_count:
                    any_failed = True
                    job.failed_chunks += failed_count

            # ── Persist embeddings ────────────────────────────────────────
            if updates:
                await chunk_repo.bulk_update_embeddings(updates)

            # ── Finalize job ──────────────────────────────────────────────
            if not any_failed:
                job.complete()
            else:
                job.fail(f"{job.failed_chunks} chunks failed to embed")
            await job_repo.update(job)
            await session.commit()

            bound.info(
                "embedding_completed",
                embedded=job.embedded_chunks,
                failed=job.failed_chunks,
            )

    async def _mark_failed(self, document_id: UUID, error: str) -> None:
        try:
            async with self._session_factory() as session:
                job_repo = PgEmbeddingJobRepository(session)
                latest = await job_repo.get_latest_by_document(document_id)
                if latest and not latest.is_terminal:
                    latest.fail(error)
                    await job_repo.update(latest)
                    await session.commit()
        except Exception:
            log.error("embedding_mark_failed_error", document_id=str(document_id))

    async def get_job_status(self, document_id: UUID) -> EmbeddingJob | None:
        async with self._session_factory() as session:
            job_repo = PgEmbeddingJobRepository(session)
            return await job_repo.get_latest_by_document(document_id)

    async def list_jobs(self, document_id: UUID) -> list[EmbeddingJob]:
        async with self._session_factory() as session:
            job_repo = PgEmbeddingJobRepository(session)
            return await job_repo.list_by_document(document_id)

    async def cancel_job(self, job_id: UUID, document_id: UUID | None = None) -> bool:
        async with self._session_factory() as session:
            job_repo = PgEmbeddingJobRepository(session)
            job = await job_repo.get_by_id(job_id)
            if job is None:
                return False
            if document_id is not None and job.document_id != document_id:
                return False
            if job.is_terminal:
                return False
            job.status = EmbeddingStatus.CANCELLED
            job.completed_at = datetime.now(UTC)
            await job_repo.update(job)
            await session.commit()
            return True
