"""IngestionService — from application/commands/ingest_document.py.

Runs as a FastAPI BackgroundTask — creates its own DB session via the
injected session factory so the request session can be closed immediately.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

if TYPE_CHECKING:
    from app.services.embedding_service import EmbeddingService

from app.models.entities import Chunk, DocumentRelation, ProcessingLog
from app.models.enums import (
    AuthorityLevel,
    DocumentStatus,
    DocumentType,
    IngestionStatus,
    RelationType,
)
from app.models.orm import DocumentModel
from app.repositories.document_store import (
    PgChunkRepository,
    PgDocumentRepository,
    PgProcessingLogRepository,
)
from app.repositories.relation_store import PgDocumentRelationRepository

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 2.0

_HIERARCHICAL = frozenset({"LAW", "CIRCULAR", "DECREE", "DECISION"})
_QA_PAIR = frozenset({"FAQ"})


def _strategy_for(doc_type: str) -> str:
    if str(doc_type) in _HIERARCHICAL:
        return "hierarchical"
    if str(doc_type) in _QA_PAIR:
        return "qa_pair"
    return "semantic"


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class IngestionPipelineService:
    """Runs the full document ingestion pipeline asynchronously."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage: Any,
        parser_registry: dict[str, Any],
        metadata_extractor: Any,
        classifier: Any,
        relation_extractor: Any,
        hierarchical_chunker: Any,
        semantic_chunker: Any,
        qa_pair_chunker: Any,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._storage = storage
        self._parsers = parser_registry
        self._metadata_extractor = metadata_extractor
        self._classifier = classifier
        self._relation_extractor = relation_extractor
        self._chunkers = {
            "hierarchical": hierarchical_chunker,
            "semantic": semantic_chunker,
            "qa_pair": qa_pair_chunker,
        }
        self._embedding_service = embedding_service

    async def process(self, document_id: UUID) -> None:
        """Entry point for background processing with retry support."""
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                await self._run_pipeline(document_id, retry_count=attempt - 1)
                return
            except Exception as exc:
                if attempt <= MAX_RETRIES:
                    log = logger.bind(document_id=str(document_id), attempt=attempt)
                    log.warning("ingestion_retry", error=str(exc))
                    await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)
                else:
                    logger.error(
                        "ingestion_failed_permanently",
                        document_id=str(document_id),
                        error=str(exc),
                        exc_info=True,
                    )
                    await self._mark_failed(document_id, str(exc))
                    return

    async def _run_pipeline(self, document_id: UUID, retry_count: int = 0) -> None:
        async with self._session_factory() as session:
            doc_repo = PgDocumentRepository(session)
            chunk_repo = PgChunkRepository(session)
            relation_repo = PgDocumentRelationRepository(session)
            log_repo = PgProcessingLogRepository(session)

            document = await doc_repo.get_by_id(document_id)
            if document is None or document.is_deleted:
                logger.warning(
                    "ingestion_skipped_missing", document_id=str(document_id)
                )
                return

            now = datetime.now(UTC)
            proc_log = ProcessingLog(
                id=_new_uuid(),
                document_id=document_id,
                status=IngestionStatus.QUEUED,
                started_at=now,
                retry_count=retry_count,
            )
            proc_log = await log_repo.create(proc_log)

            if document.status in (DocumentStatus.UPLOADED, DocumentStatus.FAILED):
                document.transition_to(DocumentStatus.PROCESSING)
                await doc_repo.update(document)
            await session.commit()

            log = logger.bind(document_id=str(document_id))
            stage_results: dict[str, Any] = {}

            # Stage 1: Parse
            proc_log.mark_stage(IngestionStatus.PARSING)
            await log_repo.update(proc_log)
            await session.commit()

            file_content = await self._storage.read(document.file_path)
            parser = self._parsers.get(document.content_type)
            if parser is None:
                raise ValueError(f"No parser for content type: {document.content_type}")

            parsed = await parser.parse(file_content, document.original_filename)
            stage_results["page_count"] = parsed.page_count
            log.info(
                "ingestion_parsed",
                pages=parsed.page_count,
                sections=len(parsed.sections),
            )

            # Stage 2: Extract metadata
            proc_log.mark_stage(IngestionStatus.EXTRACTING_METADATA)
            await log_repo.update(proc_log)
            await session.commit()

            metadata = self._metadata_extractor.extract(parsed)

            if document.doc_number is None and metadata.doc_number:
                document.doc_number = metadata.doc_number
            if document.issuing_body is None and metadata.issuing_body:
                document.issuing_body = metadata.issuing_body
            if document.issued_date is None and metadata.issued_date:
                document.issued_date = metadata.issued_date
            if document.effective_date is None and metadata.effective_date:
                document.effective_date = metadata.effective_date

            # Stage 3: Classify
            proc_log.mark_stage(IngestionStatus.CLASSIFYING)
            await log_repo.update(proc_log)
            await session.commit()

            classification = self._classifier.classify(
                raw_text=parsed.raw_text,
                doc_number=document.doc_number,
                issuing_body=document.issuing_body,
            )
            document.doc_type = DocumentType(classification.doc_type)
            document.authority_level = AuthorityLevel(classification.authority_level)
            document.updated_at = datetime.now(UTC)
            await doc_repo.update(document)
            await session.commit()

            log.info(
                "ingestion_classified",
                doc_type=classification.doc_type,
                authority_level=classification.authority_level,
            )

            # Stage 4: Extract relationships
            proc_log.mark_stage(IngestionStatus.EXTRACTING_RELATIONSHIPS)
            await log_repo.update(proc_log)
            await session.commit()

            raw_relations = self._relation_extractor.extract(parsed.raw_text)
            relations: list[DocumentRelation] = []

            for raw_rel in raw_relations:
                stmt = select(DocumentModel).where(
                    DocumentModel.doc_number == raw_rel.target_doc_number,
                    DocumentModel.deleted_at.is_(None),
                )
                result = await session.execute(stmt)
                target = result.scalar_one_or_none()
                if target is not None and target.id != document_id:
                    relations.append(
                        DocumentRelation(
                            id=_new_uuid(),
                            source_doc_id=document_id,
                            target_doc_id=target.id,
                            relation_type=RelationType(raw_rel.relation_type),
                            confidence=raw_rel.confidence,
                            description=raw_rel.description,
                        )
                    )

            stage_results["relations_found"] = len(relations)
            log.info("ingestion_relations_extracted", count=len(relations))

            # Stage 5: Chunk
            proc_log.mark_stage(IngestionStatus.CHUNKING)
            await log_repo.update(proc_log)
            await session.commit()

            strategy = _strategy_for(document.doc_type)
            chunker = self._chunkers[strategy]
            chunks: list[Chunk] = chunker.chunk(document_id=document_id, parsed=parsed)
            stage_results["chunk_count"] = len(chunks)
            log.info("ingestion_chunked", count=len(chunks), strategy=strategy)

            await chunk_repo.delete_by_document(document_id)
            await relation_repo.delete_by_document(document_id)
            await session.flush()

            if chunks:
                await chunk_repo.bulk_insert(chunks)
            if relations:
                await relation_repo.bulk_insert(relations)

            document.transition_to(DocumentStatus.READY)
            document.updated_at = datetime.now(UTC)
            await doc_repo.update(document)

            proc_log.complete(stage_results=stage_results)
            await log_repo.update(proc_log)
            await session.commit()

            log.info(
                "ingestion_completed",
                chunks=len(chunks),
                relations=len(relations),
            )

        if self._embedding_service is not None and chunks:
            _task = asyncio.create_task(  # noqa: RUF006
                self._embedding_service.embed_document(document_id)
            )

    async def _mark_failed(self, document_id: UUID, error: str) -> None:
        try:
            async with self._session_factory() as session:
                doc_repo = PgDocumentRepository(session)
                log_repo = PgProcessingLogRepository(session)

                document = await doc_repo.get_by_id(document_id)
                if document and document.status == DocumentStatus.PROCESSING:
                    document.transition_to(DocumentStatus.FAILED)
                    document.updated_at = datetime.now(UTC)
                    await doc_repo.update(document)

                last_log = await log_repo.get_latest_by_document(document_id)
                if last_log and not last_log.is_terminal:
                    last_log.fail(error)
                    await log_repo.update(last_log)

                await session.commit()
        except Exception:
            logger.error("ingestion_mark_failed_error", document_id=str(document_id))
