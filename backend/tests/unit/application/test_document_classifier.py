from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_type import DocumentType
from app.infrastructure.ingestion.document_classifier import DocumentClassifier

_CLASSIFIER = DocumentClassifier()


def test_classify_circular_by_doc_number() -> None:
    result = _CLASSIFIER.classify(raw_text="", doc_number="48/2024/TT-NHNN")
    assert result.doc_type == DocumentType.CIRCULAR
    assert result.confidence == 0.95


def test_classify_decision_by_doc_number() -> None:
    result = _CLASSIFIER.classify(raw_text="", doc_number="12/2023/QĐ-NHNN")
    assert result.doc_type == DocumentType.DECISION
    assert result.confidence == 0.95


def test_classify_decree_by_doc_number() -> None:
    result = _CLASSIFIER.classify(raw_text="", doc_number="10/2022/NĐ-CP")
    assert result.doc_type == DocumentType.DECREE
    assert result.confidence == 0.95


def test_classify_circular_by_keyword() -> None:
    result = _CLASSIFIER.classify(raw_text="thông tư quy định về ...")
    assert result.doc_type == DocumentType.CIRCULAR
    assert result.confidence == 0.80


def test_classify_law_by_keyword() -> None:
    result = _CLASSIFIER.classify(raw_text="luật các tổ chức tín dụng")
    assert result.doc_type == DocumentType.LAW
    assert result.confidence == 0.80


def test_classify_faq_by_keyword() -> None:
    result = _CLASSIFIER.classify(raw_text="câu hỏi thường gặp về tín dụng")
    assert result.doc_type == DocumentType.FAQ
    assert result.confidence == 0.80


def test_fallback_to_policy_with_low_confidence() -> None:
    result = _CLASSIFIER.classify(raw_text="tài liệu không rõ loại")
    assert result.doc_type == DocumentType.POLICY
    assert result.confidence == 0.50


def test_authority_level_nhnn_circular() -> None:
    result = _CLASSIFIER.classify(
        raw_text="thông tư",
        issuing_body="Ngân Hàng Nhà Nước Việt Nam",
    )
    assert result.authority_level == AuthorityLevel.NHNN_CIRCULAR


def test_authority_level_national_law_quoc_hoi() -> None:
    result = _CLASSIFIER.classify(
        raw_text="luật các tổ chức tín dụng",
        issuing_body="Quốc Hội",
    )
    assert result.authority_level == AuthorityLevel.NATIONAL_LAW


def test_authority_level_default_when_no_issuing_body() -> None:
    result = _CLASSIFIER.classify(raw_text="tài liệu nội bộ", doc_number=None, issuing_body=None)
    assert result.authority_level == AuthorityLevel.INTERNAL_POLICY
