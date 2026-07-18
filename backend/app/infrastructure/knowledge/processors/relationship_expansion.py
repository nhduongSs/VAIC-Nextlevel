from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.knowledge_dto import KnowledgeContext
from app.domain.entities.document import Document
from app.domain.entities.relation import DocumentRelation
from app.infrastructure.database.models.document_model import DocumentModel
from app.infrastructure.database.models.relation_model import DocumentRelationModel
from app.infrastructure.knowledge.mappers import document_to_entity, relation_to_entity

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class RelationshipExpansionProcessor:
    """BFS expansion of document relationships up to max_depth hops.

    Discovers related documents and relations not in the initial context.
    Prevents infinite recursion via a visited-ID set.
    """

    def __init__(
        self,
        session: AsyncSession,
        max_depth: int = 2,
        max_relations: int = 20,
    ) -> None:
        self._session = session
        self._max_depth = max_depth
        self._max_relations = max_relations

    async def process(self, context: KnowledgeContext) -> None:
        visited: set[UUID] = set(context.document_map.keys())

        # Docs referenced in initial relations but not yet in document_map.
        # Starting BFS from these (not from already-loaded docs) ensures depth-0
        # queries new territory instead of re-querying relations already fetched
        # by KnowledgeIntelligenceService._fetch_relations().
        frontier: set[UUID] = {
            did
            for rel in context.relationships
            for did in (rel.source_doc_id, rel.target_doc_id)
            if did not in visited
        }
        if frontier:
            initial_docs = await self._fetch_documents(list(frontier))
            context.document_map.update(initial_docs)
            visited.update(frontier)

        known_rel_ids: set[UUID] = {r.id for r in context.relationships}
        all_relations: list[DocumentRelation] = list(context.relationships)
        initial_count = len(all_relations)

        for depth in range(self._max_depth):
            if not frontier or len(all_relations) >= self._max_relations:
                break

            new_rels = await self._fetch_relations(list(frontier))
            new_doc_ids: set[UUID] = set()

            for rel in new_rels:
                if rel.id in known_rel_ids:
                    continue
                if len(all_relations) >= self._max_relations:
                    break
                all_relations.append(rel)
                known_rel_ids.add(rel.id)
                for did in (rel.source_doc_id, rel.target_doc_id):
                    if did not in visited:
                        new_doc_ids.add(did)

            if new_doc_ids:
                new_docs = await self._fetch_documents(list(new_doc_ids))
                context.document_map.update(new_docs)
                visited.update(new_doc_ids)

            frontier = new_doc_ids
            log.debug("expansion_depth", depth=depth + 1, new_docs=len(new_doc_ids))

        context.relationships = all_relations
        context.statistics["expansion_count"] = len(all_relations) - initial_count
        log.debug("relationship_expansion_done", total_relations=len(all_relations))

    async def _fetch_relations(self, doc_ids: list[UUID]) -> list[DocumentRelation]:
        if not doc_ids:
            return []
        stmt = select(DocumentRelationModel).where(
            or_(
                DocumentRelationModel.source_doc_id.in_(doc_ids),
                DocumentRelationModel.target_doc_id.in_(doc_ids),
            )
        )
        result = await self._session.execute(stmt)
        return [relation_to_entity(m) for m in result.scalars().all()]

    async def _fetch_documents(self, doc_ids: list[UUID]) -> dict[UUID, Document]:
        if not doc_ids:
            return {}
        stmt = select(DocumentModel).where(
            DocumentModel.id.in_(doc_ids),
            DocumentModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return {m.id: document_to_entity(m) for m in result.scalars().all()}
