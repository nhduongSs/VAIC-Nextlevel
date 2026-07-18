from __future__ import annotations

import asyncio
import time
from uuid import UUID

import structlog
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.knowledge_dto import ContextPackage, KnowledgeContext
from app.application.knowledge import KnowledgePipeline
from app.config import Settings
from app.config import settings as _settings
from app.domain.entities.document import Document
from app.domain.entities.relation import DocumentRelation
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.database.models.document_model import DocumentModel
from app.infrastructure.database.models.relation_model import DocumentRelationModel
from app.infrastructure.knowledge.mappers import document_to_entity, relation_to_entity
from app.infrastructure.knowledge.processors.authority_ranking import AuthorityRankingProcessor
from app.infrastructure.knowledge.processors.citation_processor import CitationProcessor
from app.infrastructure.knowledge.processors.conflict_detection import ConflictDetectionProcessor
from app.infrastructure.knowledge.processors.context_builder import ContextBuilderProcessor
from app.infrastructure.knowledge.processors.duplicate_removal import DuplicateRemovalProcessor
from app.infrastructure.knowledge.processors.relationship_expansion import (
    RelationshipExpansionProcessor,
)
from app.infrastructure.knowledge.processors.timeline_processor import TimelineProcessor
from app.infrastructure.knowledge.processors.version_resolution import VersionResolutionProcessor

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class KnowledgeIntelligenceService:
    """Orchestrates the Knowledge Intelligence pipeline.

    Responsibilities: create KnowledgeContext, execute KnowledgePipeline,
    return ContextPackage. No business logic lives here.
    """

    def __init__(self, session: AsyncSession, cfg: Settings | None = None) -> None:
        self._session = session
        self._cfg = cfg or _settings

    async def process(self, query: str, results: list[SearchResult]) -> ContextPackage:
        if not results:
            return _empty_package(query)

        t0 = time.perf_counter()
        doc_ids = list({r.document_id for r in results})

        document_map, relationships = await asyncio.gather(
            self._fetch_documents(doc_ids),
            self._fetch_relations(doc_ids),
        )

        context = KnowledgeContext(
            query=query,
            retrieved_chunks=results,
            ranked_chunks=list(results),
            document_map=document_map,
            relationships=relationships,
        )

        pipeline = self._build_pipeline()
        package = await pipeline.execute(context)

        total_ms = (time.perf_counter() - t0) * 1000
        log.info(
            "ki_process_complete",
            query=query[:80],
            input_chunks=len(results),
            output_chunks=len(package.ranked_chunks),
            citations=len(package.citations),
            timeline_entries=len(package.timeline),
            latency_ms=round(total_ms, 1),
        )
        return package

    async def health(self) -> bool:
        try:
            await self._session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    # ── Pipeline factory ─────────────────────────────────────────────────────

    def _build_pipeline(self) -> KnowledgePipeline:
        cfg = self._cfg
        return KnowledgePipeline(
            [
                AuthorityRankingProcessor(authority_weight=cfg.KI_AUTHORITY_WEIGHT),
                RelationshipExpansionProcessor(
                    session=self._session,
                    max_depth=cfg.KI_EXPANSION_DEPTH,
                    max_relations=cfg.KI_MAX_RELATIONS,
                ),
                VersionResolutionProcessor(),
                ConflictDetectionProcessor(enabled=cfg.KI_CONFLICT_DETECTION_ENABLED),
                DuplicateRemovalProcessor(),
                CitationProcessor(
                    max_citations=cfg.KI_MAX_CITATIONS,
                    enabled=cfg.KI_CITATION_ENABLED,
                ),
                TimelineProcessor(enabled=cfg.KI_TIMELINE_ENABLED),
                ContextBuilderProcessor(
                    max_chunks=cfg.KI_MAX_CONTEXT_CHUNKS,
                    max_citations=cfg.KI_MAX_CITATIONS,
                    max_relations=cfg.KI_MAX_RELATIONS,
                ),
            ]
        )

    # ── Batch data loaders ───────────────────────────────────────────────────

    async def _fetch_documents(self, doc_ids: list[UUID]) -> dict[UUID, Document]:
        if not doc_ids:
            return {}
        stmt = select(DocumentModel).where(
            DocumentModel.id.in_(doc_ids),
            DocumentModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return {m.id: document_to_entity(m) for m in result.scalars().all()}

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


def _empty_package(query: str) -> ContextPackage:
    return ContextPackage(
        query=query,
        ranked_chunks=[],
        citations=[],
        relationships=[],
        conflicts=[],
        timeline=[],
        metadata={},
        statistics={"ranked_chunk_count": 0},
    )
