from __future__ import annotations

from uuid import UUID

import structlog

from app.application.dto.knowledge_dto import KnowledgeContext
from app.domain.value_objects.relation_type import RelationType

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class VersionResolutionProcessor:
    """Detects superseded documents and penalizes their chunks in ranking.

    A document is superseded when it is the target of a REPLACES relation
    (i.e., a newer document has replaced it).
    """

    def __init__(self, superseded_penalty: float = 0.5) -> None:
        self._penalty = superseded_penalty

    async def process(self, context: KnowledgeContext) -> None:
        superseded: set[UUID] = set()
        for rel in context.relationships:
            if rel.relation_type == RelationType.REPLACES:
                superseded.add(rel.target_doc_id)

        version_notes: list[str] = []
        for chunk in context.ranked_chunks:
            if chunk.document_id in superseded:
                chunk.metadata["superseded"] = True
                chunk.metadata["version_note"] = "Đã bị thay thế bởi văn bản mới hơn"
                chunk.score = chunk.score * self._penalty
                doc = context.document_map.get(chunk.document_id)
                if doc:
                    version_notes.append(f"{doc.title} đã bị thay thế")
            else:
                chunk.metadata["superseded"] = False

        if superseded:
            context.ranked_chunks.sort(key=lambda r: r.score, reverse=True)

        if version_notes:
            context.metadata["version_notes"] = version_notes

        context.statistics["superseded_count"] = len(superseded)
        log.debug("version_resolution_done", superseded=len(superseded))
