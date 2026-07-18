import pytest

from app.domain.services.chunking_service import ChunkingService
from app.domain.value_objects.document_type import DocumentType


@pytest.mark.parametrize(
    "doc_type",
    [DocumentType.LAW, DocumentType.CIRCULAR, DocumentType.DECREE, DocumentType.DECISION],
)
def test_legal_doc_types_use_hierarchical(doc_type: DocumentType) -> None:
    assert ChunkingService.strategy_for(doc_type) == "hierarchical"


def test_faq_uses_qa_pair() -> None:
    assert ChunkingService.strategy_for(DocumentType.FAQ) == "qa_pair"


@pytest.mark.parametrize(
    "doc_type",
    [DocumentType.SOP, DocumentType.POLICY, DocumentType.MANUAL, DocumentType.PRODUCT_DOC],
)
def test_other_doc_types_use_semantic(doc_type: DocumentType) -> None:
    assert ChunkingService.strategy_for(doc_type) == "semantic"
