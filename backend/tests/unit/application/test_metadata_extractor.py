from datetime import date

from app.infrastructure.ingestion.metadata_extractor import MetadataExtractor
from app.infrastructure.ingestion.parsed_document import ParsedDocument


def _doc(text: str) -> ParsedDocument:
    return ParsedDocument(title="Test", raw_text=text, page_count=5)


_EXTRACTOR = MetadataExtractor()


def test_extract_doc_number_standard_pattern() -> None:
    text = "Thông tư số 48/2024/TT-NHNN ngày 01 tháng 01 năm 2024"
    result = _EXTRACTOR.extract(_doc(text))
    assert result.doc_number == "48/2024/TT-NHNN"


def test_extract_doc_number_with_multiple_parts() -> None:
    text = "Quyết định số 12/2020/QĐ-NHNN quy định về ..."
    result = _EXTRACTOR.extract(_doc(text))
    assert result.doc_number == "12/2020/QĐ-NHNN"


def test_extract_doc_number_missing_returns_none() -> None:
    result = _EXTRACTOR.extract(_doc("Không có số văn bản ở đây"))
    assert result.doc_number is None


def test_extract_issuing_body_nhnn() -> None:
    text = "NGÂN HÀNG NHÀ NƯỚC VIỆT NAM\nSố: 48/2024/TT-NHNN"
    result = _EXTRACTOR.extract(_doc(text))
    assert result.issuing_body is not None
    assert "Ngân Hàng" in result.issuing_body


def test_extract_issuing_body_not_found() -> None:
    result = _EXTRACTOR.extract(_doc("Tài liệu nội bộ công ty"))
    assert result.issuing_body is None


def test_extract_issued_date() -> None:
    text = "Hà Nội, ngày 15 tháng 6 năm 2024"
    result = _EXTRACTOR.extract(_doc(text))
    assert result.issued_date == date(2024, 6, 15)


def test_extract_issued_date_missing_returns_none() -> None:
    result = _EXTRACTOR.extract(_doc("Không có ngày tháng"))
    assert result.issued_date is None


def test_extract_effective_date() -> None:
    text = "Thông tư này có hiệu lực kể từ ngày 01 tháng 07 năm 2024"
    result = _EXTRACTOR.extract(_doc(text))
    assert result.effective_date == date(2024, 7, 1)


def test_extract_language_forwarded_from_parsed() -> None:
    doc = ParsedDocument(title="T", raw_text="", language="vi", page_count=3)
    result = _EXTRACTOR.extract(doc)
    assert result.language == "vi"


def test_extract_page_count_forwarded_from_parsed() -> None:
    doc = ParsedDocument(title="T", raw_text="", page_count=42)
    result = _EXTRACTOR.extract(doc)
    assert result.page_count == 42
