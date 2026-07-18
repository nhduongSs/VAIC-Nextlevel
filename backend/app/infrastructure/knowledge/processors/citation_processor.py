from __future__ import annotations

import structlog

from app.application.dto.knowledge_dto import Citation, KnowledgeContext

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_PREVIEW_LENGTH = 200


class CitationProcessor:
    """Builds a Citation for each ranked chunk using document metadata.

    Citation generation is deterministic: same input always produces same output.
    """

    def __init__(self, max_citations: int = 10, enabled: bool = True) -> None:
        self._max = max_citations
        self._enabled = enabled

    async def process(self, context: KnowledgeContext) -> None:
        if not self._enabled:
            return

        citations: list[Citation] = []
        for chunk in context.ranked_chunks[: self._max]:
            doc = context.document_map.get(chunk.document_id)
            citations.append(
                Citation(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_title=doc.title if doc else "Unknown",
                    doc_number=doc.doc_number if doc else None,
                    section_title=chunk.section_title,
                    section_number=chunk.section_number,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    authority_level=str(doc.authority_level) if doc else "UNKNOWN",
                    version=doc.version if doc else 1,
                    effective_date=doc.effective_date if doc else None,
                    content_preview=chunk.content[:_PREVIEW_LENGTH],
                )
            )

        context.citations = citations
        context.statistics["citation_count"] = len(citations)
        log.debug("citation_processor_done", citations=len(citations))
