from datetime import UTC, datetime
from uuid import uuid4

from app.domain.entities.processing_log import ProcessingLog
from app.domain.value_objects.ingestion_status import IngestionStatus


def _make_log(status: IngestionStatus = IngestionStatus.QUEUED, **kwargs: object) -> ProcessingLog:
    return ProcessingLog(
        id=uuid4(),
        document_id=uuid4(),
        status=status,
        started_at=datetime.now(UTC),
        **kwargs,  # type: ignore[arg-type]
    )


def test_initial_status_is_queued() -> None:
    log = _make_log()
    assert log.status == IngestionStatus.QUEUED


def test_is_terminal_false_for_in_progress() -> None:
    for status in (
        IngestionStatus.QUEUED,
        IngestionStatus.PARSING,
        IngestionStatus.CHUNKING,
    ):
        log = _make_log(status=status)
        assert not log.is_terminal


def test_is_terminal_true_for_completed() -> None:
    log = _make_log(status=IngestionStatus.COMPLETED)
    assert log.is_terminal


def test_is_terminal_true_for_failed() -> None:
    log = _make_log(status=IngestionStatus.FAILED)
    assert log.is_terminal


def test_mark_stage_updates_status_and_current_stage() -> None:
    log = _make_log()
    log.mark_stage(IngestionStatus.PARSING)
    assert log.status == IngestionStatus.PARSING
    assert log.current_stage == "PARSING"


def test_complete_sets_status_and_timestamp() -> None:
    log = _make_log()
    before = datetime.now(UTC)
    log.complete()
    assert log.status == IngestionStatus.COMPLETED
    assert log.completed_at is not None
    assert log.completed_at >= before


def test_complete_stores_stage_results() -> None:
    log = _make_log()
    log.complete(stage_results={"chunk_count": 42, "relations_found": 3})
    assert log.stage_results["chunk_count"] == 42
    assert log.stage_results["relations_found"] == 3


def test_complete_without_stage_results_keeps_empty_dict() -> None:
    log = _make_log()
    log.complete()
    assert log.stage_results == {}


def test_fail_sets_status_error_and_timestamp() -> None:
    log = _make_log()
    before = datetime.now(UTC)
    log.fail("Parser crashed")
    assert log.status == IngestionStatus.FAILED
    assert log.error_message == "Parser crashed"
    assert log.completed_at is not None
    assert log.completed_at >= before


def test_retry_count_default_zero() -> None:
    log = _make_log()
    assert log.retry_count == 0


def test_retry_count_can_be_set() -> None:
    log = _make_log(retry_count=2)
    assert log.retry_count == 2
