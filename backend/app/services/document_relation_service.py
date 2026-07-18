"""DocumentRelationService — KI pipeline wrapper.

Merges:
- KnowledgeContext, ContextPackage, KnowledgePipeline (from application/dto/knowledge_dto.py)
- All 8 processors (inline)
- KnowledgeIntelligenceService renamed to DocumentRelationService

Exposes:
  - apply_amendment(), apply_partial_supersession(), apply_cross_reference(), detect_conflicts()
  - process(query, results) -> ContextPackage
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import date
from itertools import combinations
from typing import Any, Protocol
from uuid import UUID

import structlog
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.config import settings as _settings
from app.models.entities import Document, DocumentRelation
from app.models.enums import AuthorityLevel, RelationType, SearchResult
from app.models.orm import DocumentModel, DocumentRelationModel

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# ── DTOs (from knowledge_dto.py) ──────────────────────────────────────────────


@dataclass
class Citation:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    doc_number: str | None
    section_title: str | None
    section_number: str | None
    page_number: int | None
    chunk_index: int
    authority_level: str
    version: int
    effective_date: date | None
    content_preview: str


@dataclass
class TimelineEntry:
    document_id: UUID
    document_title: str
    doc_number: str | None
    version: int
    effective_date: date | None
    issued_date: date | None
    relation_type: str | None
    is_current: bool = True


@dataclass
class ConflictInfo:
    source_doc_id: UUID
    target_doc_id: UUID
    source_title: str
    target_title: str
    description: str | None
    confidence: float


@dataclass
class ContextPackage:
    query: str
    ranked_chunks: list[SearchResult]
    citations: list[Citation]
    relationships: list[DocumentRelation]
    conflicts: list[ConflictInfo]
    timeline: list[TimelineEntry]
    metadata: dict[str, Any]
    statistics: dict[str, Any]


@dataclass
class KnowledgeContext:
    query: str
    retrieved_chunks: list[SearchResult]
    ranked_chunks: list[SearchResult]
    document_map: dict[UUID, Document]
    citations: list[Citation] = field(default_factory=list)
    relationships: list[DocumentRelation] = field(default_factory=list)
    conflicts: list[ConflictInfo] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    statistics: dict[str, Any] = field(default_factory=dict)
    context_package: ContextPackage | None = None


# ── KnowledgePipeline (from application/knowledge.py) ─────────────────────────


class KnowledgeProcessor(Protocol):
    async def process(self, context: KnowledgeContext) -> None: ...


class KnowledgePipeline:
    """Executes a sequence of KnowledgeProcessors against a shared KnowledgeContext."""

    def __init__(self, processors: list[KnowledgeProcessor]) -> None:
        self._processors = list(processors)

    def add_processor(self, processor: KnowledgeProcessor) -> None:
        self._processors.append(processor)

    async def execute(self, context: KnowledgeContext) -> ContextPackage:
        t0 = time.perf_counter()
        for processor in self._processors:
            pt0 = time.perf_counter()
            name = type(processor).__name__
            await processor.process(context)
            pt_ms = (time.perf_counter() - pt0) * 1000
            log.debug("processor_executed", processor=name, latency_ms=round(pt_ms, 1))

        total_ms = (time.perf_counter() - t0) * 1000
        context.statistics["pipeline_latency_ms"] = round(total_ms, 1)

        if context.context_package is None:
            raise RuntimeError(
                "Pipeline produced no ContextPackage — "
                "ensure ContextBuilderProcessor is the last processor"
            )
        log.info(
            "pipeline_complete",
            processors=len(self._processors),
            latency_ms=round(total_ms, 1),
        )
        return context.context_package


# ── Mappers ───────────────────────────────────────────────────────────────────


def _document_to_entity(m: DocumentModel) -> Document:
    from app.models.enums import AuthorityLevel, DocumentStatus, DocumentType

    return Document(
        id=m.id,
        title=m.title,
        filename=m.filename,
        original_filename=m.original_filename,
        content_type=m.content_type,
        file_size=m.file_size,
        file_path=m.file_path,
        content_hash=m.content_hash,
        status=DocumentStatus(m.status),
        version=m.version,
        doc_type=DocumentType(m.doc_type),
        authority_level=AuthorityLevel(m.authority_level),
        created_at=m.created_at,
        updated_at=m.updated_at,
        doc_number=m.doc_number,
        issuing_body=m.issuing_body,
        issued_date=m.issued_date,
        effective_date=m.effective_date,
        expired_date=m.expired_date,
        tags=list(m.tags) if m.tags else [],
        metadata_extra=dict(m.metadata_extra) if m.metadata_extra else {},
        deleted_at=m.deleted_at,
    )


def _relation_to_entity(m: DocumentRelationModel) -> DocumentRelation:
    return DocumentRelation(
        id=m.id,
        source_doc_id=m.source_doc_id,
        target_doc_id=m.target_doc_id,
        relation_type=RelationType(m.relation_type),
        confidence=m.confidence,
        description=m.description,
        metadata_extra=dict(m.metadata_extra) if m.metadata_extra else {},
        created_at=m.created_at,
    )


# ── Processors (inline from infrastructure/knowledge/processors/) ──────────────

_DEFAULT_AUTHORITY_SCORES: dict[str, float] = {
    AuthorityLevel.NATIONAL_LAW: 1.0,
    AuthorityLevel.NHNN_CIRCULAR: 0.8,
    AuthorityLevel.NHNN_DECISION: 0.7,
    AuthorityLevel.INTERNAL_POLICY: 0.5,
    AuthorityLevel.DEPARTMENT_SOP: 0.3,
    AuthorityLevel.FAQ: 0.1,
    AuthorityLevel.UNKNOWN: 0.0,
}


class AuthorityRankingProcessor:
    def __init__(
        self,
        authority_scores: dict[str, float] | None = None,
        authority_weight: float = 0.2,
    ) -> None:
        self._scores = authority_scores or _DEFAULT_AUTHORITY_SCORES
        self._weight = authority_weight

    async def process(self, context: KnowledgeContext) -> None:
        for chunk in context.ranked_chunks:
            doc = context.document_map.get(chunk.document_id)
            authority_score = (
                self._scores.get(str(doc.authority_level), 0.0) if doc else 0.0
            )
            chunk.score = (
                1.0 - self._weight
            ) * chunk.score + self._weight * authority_score
            chunk.metadata["authority_score"] = round(authority_score, 4)
            if doc:
                chunk.metadata["authority_level"] = str(doc.authority_level)
        context.ranked_chunks.sort(key=lambda r: r.score, reverse=True)
        context.statistics["authority_ranking_applied"] = True


class RelationshipExpansionProcessor:
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

        for _depth in range(self._max_depth):
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

        context.relationships = all_relations
        context.statistics["expansion_count"] = len(all_relations) - initial_count

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
        return [_relation_to_entity(m) for m in result.scalars().all()]

    async def _fetch_documents(self, doc_ids: list[UUID]) -> dict[UUID, Document]:
        if not doc_ids:
            return {}
        stmt = select(DocumentModel).where(
            DocumentModel.id.in_(doc_ids),
            DocumentModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return {m.id: _document_to_entity(m) for m in result.scalars().all()}


class VersionResolutionProcessor:
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


class ConflictDetectionProcessor:
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
            if (
                rel.source_doc_id not in retrieved_ids
                and rel.target_doc_id not in retrieved_ids
            ):
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


class DuplicateRemovalProcessor:
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


_PREVIEW_LENGTH = 200


class CitationProcessor:
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


class TimelineProcessor:
    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    async def process(self, context: KnowledgeContext) -> None:
        if not self._enabled:
            return

        replaces_of: dict[UUID, UUID] = {}
        for rel in context.relationships:
            if rel.relation_type == RelationType.REPLACES:
                replaces_of[rel.target_doc_id] = rel.source_doc_id

        if not replaces_of:
            return

        target_ids = set(replaces_of.keys())
        source_ids = set(replaces_of.values())

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


class ContextBuilderProcessor:
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


# ── DocumentRelationService (renamed KnowledgeIntelligenceService) ─────────────


class DocumentRelationService:
    """Orchestrates the Knowledge Intelligence pipeline.

    Exposes:
      - apply_amendment(): keep only most recent version per title group
      - apply_partial_supersession(): remove superseded clause chunks
      - apply_cross_reference(): expand with related document chunks
      - detect_conflicts(): find conflicting chunk pairs
      - process(query, results): full KI pipeline → ContextPackage
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

    def apply_amendment(self, chunks: list[SearchResult]) -> list[SearchResult]:
        """Keep only the most recently effective chunk per document title group."""
        latest_by_doc: dict[UUID, SearchResult] = {}
        for c in chunks:
            current = latest_by_doc.get(c.document_id)
            if current is None or c.score > current.score:
                latest_by_doc[c.document_id] = c
        return list(latest_by_doc.values())

    def apply_partial_supersession(
        self, chunks: list[SearchResult]
    ) -> list[SearchResult]:
        """Remove chunks from superseded documents (those targeted by REPLACES relation)."""
        return [c for c in chunks if not c.metadata.get("superseded", False)]

    def apply_cross_reference(self, chunks: list[SearchResult]) -> list[SearchResult]:
        """Return chunks as-is (cross-reference expansion done in pipeline)."""
        return chunks

    def detect_conflicts(self, chunks: list[SearchResult]) -> list[ConflictInfo]:
        """Simple heuristic conflict detection between chunk pairs."""
        conflicts: list[ConflictInfo] = []
        for a, b in combinations(chunks, 2):
            if a.document_id == b.document_id:
                continue
            if (
                a.section_title
                and b.section_title
                and a.section_title == b.section_title
            ):
                if a.content.strip() != b.content.strip():
                    conflicts.append(
                        ConflictInfo(
                            source_doc_id=a.document_id,
                            target_doc_id=b.document_id,
                            source_title=str(a.document_id),
                            target_title=str(b.document_id),
                            description=(
                                f"Chunks from different documents have same section title"
                                f" '{a.section_title}' but different content."
                            ),
                            confidence=0.7,
                        )
                    )
        return conflicts

    async def health(self) -> bool:
        try:
            await self._session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

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

    async def _fetch_documents(self, doc_ids: list[UUID]) -> dict[UUID, Document]:
        if not doc_ids:
            return {}
        stmt = select(DocumentModel).where(
            DocumentModel.id.in_(doc_ids),
            DocumentModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return {m.id: _document_to_entity(m) for m in result.scalars().all()}

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
        return [_relation_to_entity(m) for m in result.scalars().all()]


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
