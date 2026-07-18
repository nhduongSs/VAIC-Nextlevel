from app.domain.value_objects.document_type import DocumentType

_HIERARCHICAL = frozenset(
    {DocumentType.LAW, DocumentType.CIRCULAR, DocumentType.DECREE, DocumentType.DECISION}
)
_QA_PAIR = frozenset({DocumentType.FAQ})


class ChunkingService:
    """Selects the chunking strategy name for a given document type."""

    @staticmethod
    def strategy_for(doc_type: DocumentType) -> str:
        if doc_type in _HIERARCHICAL:
            return "hierarchical"
        if doc_type in _QA_PAIR:
            return "qa_pair"
        return "semantic"
