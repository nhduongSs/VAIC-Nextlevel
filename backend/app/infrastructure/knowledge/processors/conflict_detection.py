from __future__ import annotations

import structlog

from app.application.dto.knowledge_dto import ConflictInfo, KnowledgeContext
from app.domain.value_objects.relation_type import RelationType

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class ConflictDetectionProcessor:
    """Detects CONFLICTS_WITH relations among retrieved documents.

    Populates context.conflicts without attempting automatic resolution.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    async def process(self, context: KnowledgeContext) -> None:
        if not self._enabled:
            context.statistics["conflict_count"] = 0
            return
        retrieved_ids = {c.document_id for c in context.ranked_chunks}
        conflicts: list[ConflictInfo] = []

        for rel in context.relationships:
            if rel.relation_type != RelationType.CONFLICTS_WITH:
                continue
            # Only report conflicts involving at least one retrieved document
            if rel.source_doc_id not in retrieved_ids and rel.target_doc_id not in retrieved_ids:
                continue
            src_doc = context.document_map.get(rel.source_doc_id)
            tgt_doc = context.document_map.get(rel.target_doc_id)
            conflicts.append(
                ConflictInfo(
                    source_doc_id=rel.source_doc_id,
                    target_doc_id=rel.target_doc_id,
                    source_title=src_doc.title if src_doc else str(rel.source_doc_id),
                    target_title=tgt_doc.title if tgt_doc else str(rel.target_doc_id),
                    description=rel.description,
                    confidence=rel.confidence,
                )
            )

        context.conflicts = conflicts
        if conflicts:
            context.metadata["has_conflicts"] = True

        context.statistics["conflict_count"] = len(conflicts)
        log.debug("conflict_detection_done", conflicts=len(conflicts))
