from __future__ import annotations

import structlog

from app.application.dto.knowledge_dto import ContextPackage, KnowledgeContext

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class ContextBuilderProcessor:
    """Assembles the final ContextPackage from all context fields.

    Enforces per-list size limits before assembling. Must be the last
    processor in the pipeline.
    """

    def __init__(
        self,
        max_chunks: int = 15,
        max_citations: int = 10,
        max_relations: int = 20,
    ) -> None:
        self._max_chunks = max_chunks
        self._max_citations = max_citations
        self._max_relations = max_relations

    async def process(self, context: KnowledgeContext) -> None:
        ranked = context.ranked_chunks[: self._max_chunks]
        citations = context.citations[: self._max_citations]
        relationships = context.relationships[: self._max_relations]

        context.statistics.update(
            {
                "ranked_chunk_count": len(ranked),
                "citation_count": len(citations),
                "relationship_count": len(relationships),
                "conflict_count": len(context.conflicts),
                "timeline_entry_count": len(context.timeline),
            }
        )

        context.context_package = ContextPackage(
            query=context.query,
            ranked_chunks=ranked,
            citations=citations,
            relationships=relationships,
            conflicts=context.conflicts,
            timeline=context.timeline,
            metadata=context.metadata,
            statistics=context.statistics,
        )

        log.debug(
            "context_built",
            chunks=len(ranked),
            citations=len(citations),
            relations=len(relationships),
            conflicts=len(context.conflicts),
            timeline=len(context.timeline),
        )
