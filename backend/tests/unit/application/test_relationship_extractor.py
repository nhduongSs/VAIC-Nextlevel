from app.domain.value_objects.relation_type import RelationType
from app.infrastructure.ingestion.relationship_extractor import RelationshipExtractor

_EXTRACTOR = RelationshipExtractor()


def test_extract_replaces_relation() -> None:
    text = "Thông tư này thay thế Thông tư số 12/2018/TT-NHNN."
    results = _EXTRACTOR.extract(text)
    types = [r.relation_type for r in results]
    numbers = [r.target_doc_number for r in results]
    assert RelationType.REPLACES in types
    assert "12/2018/TT-NHNN" in numbers


def test_extract_amends_relation() -> None:
    text = "Sửa đổi một số điều của Thông tư 05/2019/TT-NHNN."
    results = _EXTRACTOR.extract(text)
    types = [r.relation_type for r in results]
    assert RelationType.AMENDS in types


def test_extract_references_relation() -> None:
    text = "Căn cứ Thông tư số 23/2010/TT-NHNN và các quy định hiện hành."
    results = _EXTRACTOR.extract(text)
    types = [r.relation_type for r in results]
    assert RelationType.REFERENCES in types


def test_no_duplicates_same_relation_same_doc() -> None:
    text = "Thông tư này thay thế 48/2018/TT-NHNN. Quy định thay thế 48/2018/TT-NHNN kể từ ngày ký."
    results = _EXTRACTOR.extract(text)
    replaces = [r for r in results if r.relation_type == RelationType.REPLACES]
    targets = [r.target_doc_number for r in replaces]
    assert targets.count("48/2018/TT-NHNN") == 1


def test_replaces_has_higher_confidence_than_references() -> None:
    text = "Thông tư này thay thế 10/2020/TT-NHNN. Căn cứ Thông tư số 03/2019/TT-BTC."
    results = _EXTRACTOR.extract(text)
    replaces = next(r for r in results if r.relation_type == RelationType.REPLACES)
    references = next(r for r in results if r.relation_type == RelationType.REFERENCES)
    assert replaces.confidence > references.confidence


def test_empty_text_returns_empty_list() -> None:
    assert _EXTRACTOR.extract("") == []


def test_no_matching_patterns_returns_empty_list() -> None:
    assert _EXTRACTOR.extract("Văn bản không có tham chiếu nào.") == []
