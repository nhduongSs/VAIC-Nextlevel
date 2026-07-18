from __future__ import annotations

from uuid import UUID

import structlog

from app.application.dto.knowledge_dto import KnowledgeContext

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class DuplicateRemovalProcessor:
    """Removes duplicate chunks from ranked_chunks by chunk_id.

    Assumes ranked_chunks is sorted descending by score; keeps the first
    (highest-scored) occurrence of each chunk_id.
    """

    async def process(self, context: KnowledgeContext) -> None:
        seen: set[UUID] = set()
        deduped = []
        removed = 0

        for chunk in context.ranked_chunks:
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                deduped.append(chunk)
            else:
                removed += 1

        context.ranked_chunks = deduped
        context.statistics["duplicates_removed"] = removed
        log.debug("duplicate_removal_done", removed=removed, remaining=len(deduped))
