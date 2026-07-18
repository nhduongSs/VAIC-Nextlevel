"""Unit tests for EmbeddingService — all I/O is mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.services.embedding_service import EmbeddingService
from app.domain.entities.chunk import Chunk
from app.domain.entities.embedding_job import EmbeddingJob
from app.domain.value_objects.chunk_type import ChunkType
from app.domain.value_objects.embedding_status import EmbeddingStatus
from app.infrastructure.ai.embedding.embedding_provider import EmbeddingProvider


def _make_chunk(idx: int = 0) -> Chunk:
    from datetime import UTC, datetime

    return Chunk(
        id=uuid4(),
        document_id=uuid4(),
        content=f"chunk text {idx}",
        chunk_index=idx,
        chunk_type=ChunkType.PARAGRAPH,
        created_at=datetime.now(UTC),
    )


def _make_job(status: EmbeddingStatus = EmbeddingStatus.PENDING) -> EmbeddingJob:
    from datetime import UTC, datetime

    return EmbeddingJob(
        id=uuid4(),
        document_id=uuid4(),
        status=status,
        model_name="BAAI/bge-m3",
        created_at=datetime.now(UTC),
    )


class _FakeProvider(EmbeddingProvider):
    """Minimal in-process provider for unit tests."""

    model_name = "BAAI/bge-m3"
    dimensions = 1024

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1024 for _ in texts]

    async def health_check(self) -> bool:
        return True


class _FailingProvider(EmbeddingProvider):
    """Provider that always raises on embed()."""

    model_name = "BAAI/bge-m3"
    dimensions = 1024

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("Provider unavailable")

    async def health_check(self) -> bool:
        return False


class _WrongDimProvider(EmbeddingProvider):
    """Provider that returns wrong-dimension vectors (simulates misconfigured service)."""

    model_name = "BAAI/bge-m3"
    dimensions = 1024

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 512 for _ in texts]  # wrong: 512 instead of 1024

    async def health_check(self) -> bool:
        return True


@pytest.fixture
def provider() -> _FakeProvider:
    return _FakeProvider()


def _make_service(prov: EmbeddingProvider, **kwargs: object) -> EmbeddingService:
    session_factory = MagicMock()
    return EmbeddingService(
        session_factory=session_factory,
        provider=prov,
        batch_size=kwargs.get("batch_size", 2),  # type: ignore[arg-type]
        max_concurrency=kwargs.get("max_concurrency", 2),  # type: ignore[arg-type]
        max_retries=kwargs.get("max_retries", 1),  # type: ignore[arg-type]
    )


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.mark.asyncio
async def test_embed_document_skips_when_no_chunks(provider: _FakeProvider) -> None:
    svc = _make_service(provider)
    chunk_repo = AsyncMock()
    chunk_repo.get_by_document.return_value = []
    job_repo = AsyncMock()

    session = _mock_session()
    svc._session_factory = MagicMock(return_value=session)

    with (
        patch(
            "app.application.services.embedding_service.PgChunkRepository",
            return_value=chunk_repo,
        ),
        patch(
            "app.application.services.embedding_service.PgEmbeddingJobRepository",
            return_value=job_repo,
        ),
    ):
        await svc._run(uuid4())

    job_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_embed_document_creates_and_completes_job(provider: _FakeProvider) -> None:
    chunks = [_make_chunk(i) for i in range(3)]
    job = _make_job()
    job.total_chunks = len(chunks)

    chunk_repo = AsyncMock()
    chunk_repo.get_by_document.return_value = chunks
    chunk_repo.bulk_update_embeddings.return_value = 3
    job_repo = AsyncMock()
    job_repo.create.return_value = job
    job_repo.update.return_value = job

    session = _mock_session()
    svc = _make_service(provider)
    svc._session_factory = MagicMock(return_value=session)

    with (
        patch(
            "app.application.services.embedding_service.PgChunkRepository",
            return_value=chunk_repo,
        ),
        patch(
            "app.application.services.embedding_service.PgEmbeddingJobRepository",
            return_value=job_repo,
        ),
    ):
        await svc._run(uuid4())

    job_repo.create.assert_called_once()
    chunk_repo.bulk_update_embeddings.assert_called_once()
    assert job.status == EmbeddingStatus.COMPLETED


@pytest.mark.asyncio
async def test_embed_document_marks_failed_when_all_batches_fail() -> None:
    """All batches fail → job ends FAILED with correct failed_chunks count."""
    failing = _FailingProvider()
    chunks = [_make_chunk(i) for i in range(4)]
    job = _make_job()
    job.total_chunks = len(chunks)

    chunk_repo = AsyncMock()
    chunk_repo.get_by_document.return_value = chunks
    job_repo = AsyncMock()
    job_repo.create.return_value = job
    job_repo.update.return_value = job

    session = _mock_session()
    svc = _make_service(failing, batch_size=2)
    svc._session_factory = MagicMock(return_value=session)

    with (
        patch(
            "app.application.services.embedding_service.PgChunkRepository",
            return_value=chunk_repo,
        ),
        patch(
            "app.application.services.embedding_service.PgEmbeddingJobRepository",
            return_value=job_repo,
        ),
    ):
        await svc._run(uuid4())

    assert job.status == EmbeddingStatus.FAILED
    assert job.failed_chunks == 4
    chunk_repo.bulk_update_embeddings.assert_not_called()


@pytest.mark.asyncio
async def test_get_job_status_returns_latest(provider: _FakeProvider) -> None:
    job = _make_job(status=EmbeddingStatus.COMPLETED)
    job_repo = AsyncMock()
    job_repo.get_latest_by_document.return_value = job

    session = _mock_session()
    svc = _make_service(provider)
    svc._session_factory = MagicMock(return_value=session)

    with patch(
        "app.application.services.embedding_service.PgEmbeddingJobRepository",
        return_value=job_repo,
    ):
        result = await svc.get_job_status(uuid4())

    assert result is not None
    assert result.status == EmbeddingStatus.COMPLETED


@pytest.mark.asyncio
async def test_cancel_job_returns_false_for_terminal(provider: _FakeProvider) -> None:
    job = _make_job(status=EmbeddingStatus.COMPLETED)
    job_repo = AsyncMock()
    job_repo.get_by_id.return_value = job

    session = _mock_session()
    svc = _make_service(provider)
    svc._session_factory = MagicMock(return_value=session)

    with patch(
        "app.application.services.embedding_service.PgEmbeddingJobRepository",
        return_value=job_repo,
    ):
        result = await svc.cancel_job(uuid4())

    assert result is False


@pytest.mark.asyncio
async def test_cancel_job_returns_false_when_not_found(provider: _FakeProvider) -> None:
    job_repo = AsyncMock()
    job_repo.get_by_id.return_value = None

    session = _mock_session()
    svc = _make_service(provider)
    svc._session_factory = MagicMock(return_value=session)

    with patch(
        "app.application.services.embedding_service.PgEmbeddingJobRepository",
        return_value=job_repo,
    ):
        result = await svc.cancel_job(uuid4())

    assert result is False


@pytest.mark.asyncio
async def test_cancel_job_cancels_running_job(provider: _FakeProvider) -> None:
    job = _make_job(status=EmbeddingStatus.RUNNING)
    job_repo = AsyncMock()
    job_repo.get_by_id.return_value = job
    job_repo.update.return_value = job

    session = _mock_session()
    svc = _make_service(provider)
    svc._session_factory = MagicMock(return_value=session)

    with patch(
        "app.application.services.embedding_service.PgEmbeddingJobRepository",
        return_value=job_repo,
    ):
        result = await svc.cancel_job(uuid4())

    assert result is True
    assert job.status == EmbeddingStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_job_returns_false_for_wrong_document(provider: _FakeProvider) -> None:
    """cancel_job rejects job that belongs to a different document."""
    doc_id = uuid4()
    other_doc_id = uuid4()
    job = _make_job(status=EmbeddingStatus.RUNNING)
    job.document_id = other_doc_id  # belongs to a different document

    job_repo = AsyncMock()
    job_repo.get_by_id.return_value = job
    job_repo.update.return_value = job

    session = _mock_session()
    svc = _make_service(provider)
    svc._session_factory = MagicMock(return_value=session)

    with patch(
        "app.application.services.embedding_service.PgEmbeddingJobRepository",
        return_value=job_repo,
    ):
        result = await svc.cancel_job(job.id, document_id=doc_id)

    assert result is False
    assert job.status == EmbeddingStatus.RUNNING  # unchanged
