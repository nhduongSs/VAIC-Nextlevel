from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.commands.ingest_document import IngestionPipelineService
from app.application.services.document_service import DocumentService
from app.application.services.embedding_service import EmbeddingService
from app.config import settings
from app.infrastructure.ai.embedding.bge_m3_client import BgeM3Client
from app.infrastructure.database.base import AsyncSessionFactory, get_db_session
from app.infrastructure.database.repositories.pg_chunk_repo import PgChunkRepository
from app.infrastructure.database.repositories.pg_document_repo import PgDocumentRepository
from app.infrastructure.database.repositories.pg_embedding_job_repo import (
    PgEmbeddingJobRepository,
)
from app.infrastructure.database.repositories.pg_processing_log_repo import (
    PgProcessingLogRepository,
)
from app.infrastructure.database.repositories.pg_relation_repo import PgDocumentRelationRepository
from app.infrastructure.ingestion.chunkers.hierarchical_chunker import HierarchicalChunker
from app.infrastructure.ingestion.chunkers.qa_pair_chunker import QAPairChunker
from app.infrastructure.ingestion.chunkers.semantic_chunker import SemanticChunker
from app.infrastructure.ingestion.document_classifier import DocumentClassifier
from app.infrastructure.ingestion.metadata_extractor import MetadataExtractor
from app.infrastructure.ingestion.ocr.null_ocr_provider import NullOCRProvider
from app.infrastructure.ingestion.parsers.document_parser import DocumentParser
from app.infrastructure.ingestion.parsers.docx_parser import DocxParser
from app.infrastructure.ingestion.parsers.pdf_parser import PdfParser
from app.infrastructure.ingestion.parsers.txt_parser import TxtParser
from app.infrastructure.ingestion.relationship_extractor import RelationshipExtractor
from app.infrastructure.storage.local_storage_provider import LocalStorageProvider
from app.infrastructure.storage.storage_provider import StorageProvider

# ── Database ─────────────────────────────────────────────────────────────────

DBSession = Annotated[AsyncSession, Depends(get_db_session)]

# ── Storage ───────────────────────────────────────────────────────────────────

_ocr = NullOCRProvider()
_docx_parser = DocxParser(ocr=_ocr)
_pdf_parser = PdfParser(ocr=_ocr)
_txt_parser = TxtParser()

_PARSER_REGISTRY: dict[str, DocumentParser] = {}
for _parser in (_docx_parser, _pdf_parser, _txt_parser):
    for _ct in _parser.supported_content_types:
        _PARSER_REGISTRY[_ct] = _parser

_metadata_extractor = MetadataExtractor()
_classifier = DocumentClassifier()
_relation_extractor = RelationshipExtractor()
_hierarchical_chunker = HierarchicalChunker()
_semantic_chunker = SemanticChunker()
_qa_pair_chunker = QAPairChunker()

_bge_m3_client = BgeM3Client(
    base_url=settings.EMBEDDING_SERVICE_URL,
    timeout=settings.EMBEDDING_TIMEOUT,
)
_embedding_service = EmbeddingService(
    session_factory=AsyncSessionFactory,
    provider=_bge_m3_client,
    batch_size=settings.EMBEDDING_BATCH_SIZE,
    max_concurrency=settings.EMBEDDING_MAX_CONCURRENCY,
    max_retries=settings.EMBEDDING_MAX_RETRIES,
    retry_delay=settings.EMBEDDING_RETRY_DELAY,
    batch_timeout=settings.EMBEDDING_BATCH_TIMEOUT,
)


def get_storage_provider() -> StorageProvider:
    return LocalStorageProvider(settings.UPLOAD_DIR)


def get_embedding_service() -> EmbeddingService:
    return _embedding_service


def get_embedding_job_repository(session: DBSession) -> PgEmbeddingJobRepository:
    return PgEmbeddingJobRepository(session)


# ── Document ──────────────────────────────────────────────────────────────────


def get_document_repository(session: DBSession) -> PgDocumentRepository:
    return PgDocumentRepository(session)


def get_document_service(
    repo: Annotated[PgDocumentRepository, Depends(get_document_repository)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> DocumentService:
    return DocumentService(repo, storage)


# ── Ingestion ──────────────────────────────────────────────────────────────────


def get_chunk_repository(session: DBSession) -> PgChunkRepository:
    return PgChunkRepository(session)


def get_relation_repository(session: DBSession) -> PgDocumentRelationRepository:
    return PgDocumentRelationRepository(session)


def get_processing_log_repository(session: DBSession) -> PgProcessingLogRepository:
    return PgProcessingLogRepository(session)


def get_ingestion_pipeline_service() -> IngestionPipelineService:
    return IngestionPipelineService(
        session_factory=AsyncSessionFactory,
        storage=get_storage_provider(),
        parser_registry=_PARSER_REGISTRY,
        metadata_extractor=_metadata_extractor,
        classifier=_classifier,
        relation_extractor=_relation_extractor,
        hierarchical_chunker=_hierarchical_chunker,
        semantic_chunker=_semantic_chunker,
        qa_pair_chunker=_qa_pair_chunker,
        embedding_service=_embedding_service,
    )
