from datetime import UTC, datetime
from uuid import uuid4

from app.domain.entities.embedding_job import EmbeddingJob
from app.domain.value_objects.embedding_status import EmbeddingStatus


def _make_job(status: EmbeddingStatus = EmbeddingStatus.PENDING, **kwargs: object) -> EmbeddingJob:
    return EmbeddingJob(
        id=uuid4(),
        document_id=uuid4(),
        status=status,
        model_name="BAAI/bge-m3",
        **kwargs,  # type: ignore[arg-type]
    )


def test_initial_status_is_pending() -> None:
    job = _make_job()
    assert job.status == EmbeddingStatus.PENDING


def test_is_terminal_false_for_pending_running_retrying() -> None:
    for s in (EmbeddingStatus.PENDING, EmbeddingStatus.RUNNING, EmbeddingStatus.RETRYING):
        job = _make_job(status=s)
        assert not job.is_terminal


def test_is_terminal_true_for_completed() -> None:
    job = _make_job(status=EmbeddingStatus.COMPLETED)
    assert job.is_terminal


def test_is_terminal_true_for_failed() -> None:
    job = _make_job(status=EmbeddingStatus.FAILED)
    assert job.is_terminal


def test_is_terminal_true_for_cancelled() -> None:
    job = _make_job(status=EmbeddingStatus.CANCELLED)
    assert job.is_terminal


def test_progress_pct_zero_when_no_chunks() -> None:
    job = _make_job(total_chunks=0, embedded_chunks=0)
    assert job.progress_pct == 0.0


def test_progress_pct_calculation() -> None:
    job = _make_job(total_chunks=10, embedded_chunks=7)
    assert job.progress_pct == 70.0


def test_progress_pct_rounded_to_one_decimal() -> None:
    job = _make_job(total_chunks=3, embedded_chunks=1)
    assert job.progress_pct == 33.3


def test_start_sets_status_and_timestamp() -> None:
    job = _make_job()
    before = datetime.now(UTC)
    job.start()
    assert job.status == EmbeddingStatus.RUNNING
    assert job.started_at is not None
    assert job.started_at >= before


def test_complete_sets_status_and_timestamp() -> None:
    job = _make_job()
    before = datetime.now(UTC)
    job.complete()
    assert job.status == EmbeddingStatus.COMPLETED
    assert job.completed_at is not None
    assert job.completed_at >= before


def test_fail_sets_status_error_and_timestamp() -> None:
    job = _make_job()
    before = datetime.now(UTC)
    job.fail("timeout")
    assert job.status == EmbeddingStatus.FAILED
    assert job.error_message == "timeout"
    assert job.completed_at is not None
    assert job.completed_at >= before


def test_mark_retrying_increments_retry_count() -> None:
    job = _make_job(retry_count=1)
    job.mark_retrying()
    assert job.status == EmbeddingStatus.RETRYING
    assert job.retry_count == 2


def test_default_retry_count_zero() -> None:
    job = _make_job()
    assert job.retry_count == 0
