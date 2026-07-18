from app.models.schemas import DocStatus, RetrievedChunk
from app.services.document_relation_service import DocumentRelationService


def _chunk(**overrides) -> RetrievedChunk:
    base = dict(
        content="nội dung mẫu",
        doc_id="VB-001",
        title="Biểu lãi suất tiền gửi",
        clause="Điều 1. Lãi suất kỳ hạn 6 tháng",
        effective_date="2026-01-01",
        status=DocStatus.HIEU_LUC,
        score=0.9,
    )
    base.update(overrides)
    return RetrievedChunk(**base)


def test_amendment_keeps_latest_effective_date():
    service = DocumentRelationService()
    old = _chunk(effective_date="2025-01-01")
    new = _chunk(effective_date="2026-01-01")

    kept = service.apply_amendment([old, new])

    assert kept == [new]


def test_partial_supersession_drops_expired_status():
    service = DocumentRelationService()
    expired = _chunk(status=DocStatus.HET_HIEU_LUC)
    active = _chunk(doc_id="VB-002", status=DocStatus.HIEU_LUC)

    kept = service.apply_partial_supersession([expired, active])

    assert kept == [active]


def test_detect_conflicts_flags_same_topic_different_content():
    service = DocumentRelationService()
    a = _chunk(doc_id="VB-001", content="Lãi suất 6 tháng là 5.5%")
    b = _chunk(doc_id="VB-002", content="Lãi suất 6 tháng là 6.0%")

    conflicts = service.detect_conflicts([a, b])

    assert len(conflicts) == 1
    assert set(conflicts[0].conflicting_sources) == {"VB-001", "VB-002"}
