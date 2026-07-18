from __future__ import annotations

from uuid import UUID

import structlog

from app.application.dto.knowledge_dto import KnowledgeContext, TimelineEntry
from app.domain.value_objects.relation_type import RelationType

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class TimelineProcessor:
    """Builds a chronological document history from REPLACES relations.

    Traverses the replacement chain from oldest to newest document.
    Circular references are detected via a visited-ID set.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    async def process(self, context: KnowledgeContext) -> None:
        if not self._enabled:
            return

        # replaces_of[target_id] = source_id  (source is the newer replacement)
        replaces_of: dict[UUID, UUID] = {}
        for rel in context.relationships:
            if rel.relation_type == RelationType.REPLACES:
                replaces_of[rel.target_doc_id] = rel.source_doc_id

        if not replaces_of:
            return

        target_ids = set(replaces_of.keys())
        source_ids = set(replaces_of.values())

        # Oldest doc: it's a target but not a source of any REPLACES relation
        oldest_candidates = target_ids - source_ids
        if not oldest_candidates:
            log.warning("timeline_circular_reference_detected")
            return

        start_id = next(iter(oldest_candidates))
        chain: list[TimelineEntry] = []
        visited: set[UUID] = set()
        current_id = start_id

        while current_id not in visited:
            visited.add(current_id)
            doc = context.document_map.get(current_id)
            is_current = current_id not in target_ids
            in_chain_as_source = current_id in source_ids

            chain.append(
                TimelineEntry(
                    document_id=current_id,
                    document_title=doc.title if doc else str(current_id),
                    doc_number=doc.doc_number if doc else None,
                    version=doc.version if doc else 1,
                    effective_date=doc.effective_date if doc else None,
                    issued_date=doc.issued_date if doc else None,
                    relation_type="REPLACES" if in_chain_as_source else None,
                    is_current=is_current,
                )
            )

            next_id = replaces_of.get(current_id)
            if next_id is None:
                break
            current_id = next_id

        context.timeline = chain
        context.statistics["timeline_entries"] = len(chain)
        log.debug("timeline_built", entries=len(chain))
