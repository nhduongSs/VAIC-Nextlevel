"""Dependency injection — from app/dependencies.py, updated to use new paths."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

if TYPE_CHECKING:
    from app.services.chat_service import ChatService

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionFactory, get_db_session
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token

# ── Storage ───────────────────────────────────────────────────────────────────
from app.infrastructure.ingestion.chunkers.hierarchical_chunker import (
    HierarchicalChunker,
)
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
from app.models.orm import UserModel
from app.repositories.bank_product_store import PgBankProductRepository
from app.repositories.document_store import (
    PgChunkRepository,
    PgDocumentRepository,
    PgEmbeddingJobRepository,
    PgProcessingLogRepository,
)
from app.repositories.relation_store import PgDocumentRelationRepository
from app.repositories.user_store import PgUserRepository
from app.repositories.vector_store import EmbeddingClient
from app.services.auth_service import AuthService
from app.services.document_relation_service import DocumentRelationService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.generation.llm.deepseek_client import DeepSeekClient
from app.generation.llm.deepseek_service import DeepSeekService
from app.generation.prompt.builder import PromptBuilder
from app.generation.prompt.config import PromptConfig
from app.generation.response.formatter import ResponseFormatter
from app.services.guardrail_service import GuardrailService
from app.services.ingestion_service import IngestionPipelineService
from app.services.rag_service import RAGService

# ── Database ─────────────────────────────────────────────────────────────────

DBSession = Annotated[AsyncSession, Depends(get_db_session)]

# ── Singletons ────────────────────────────────────────────────────────────────

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

_embedding_client = EmbeddingClient(
    base_url=settings.EMBEDDING_SERVICE_URL,
    timeout=settings.EMBEDDING_TIMEOUT,
)
_embedding_service = EmbeddingService(
    session_factory=AsyncSessionFactory,
    provider=_embedding_client,
    batch_size=settings.EMBEDDING_BATCH_SIZE,
    max_concurrency=settings.EMBEDDING_MAX_CONCURRENCY,
    max_retries=settings.EMBEDDING_MAX_RETRIES,
    retry_delay=settings.EMBEDDING_RETRY_DELAY,
    batch_timeout=settings.EMBEDDING_BATCH_TIMEOUT,
)


# ── Provider functions ────────────────────────────────────────────────────────


def get_storage_provider() -> StorageProvider:
    return LocalStorageProvider(settings.UPLOAD_DIR)


def get_embedding_service() -> EmbeddingService:
    return _embedding_service


def get_embedding_client() -> EmbeddingClient:
    return _embedding_client


def get_embedding_job_repository(session: DBSession) -> PgEmbeddingJobRepository:
    return PgEmbeddingJobRepository(session)


def get_document_repository(session: DBSession) -> PgDocumentRepository:
    return PgDocumentRepository(session)


def get_document_service(
    repo: Annotated[PgDocumentRepository, Depends(get_document_repository)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> DocumentService:
    return DocumentService(repo, storage)


def get_chunk_repository(session: DBSession) -> PgChunkRepository:
    return PgChunkRepository(session)


def get_relation_repository(session: DBSession) -> PgDocumentRelationRepository:
    return PgDocumentRelationRepository(session)


def get_bank_product_repository(session: DBSession) -> PgBankProductRepository:
    return PgBankProductRepository(session)


def get_processing_log_repository(session: DBSession) -> PgProcessingLogRepository:
    return PgProcessingLogRepository(session)


def get_user_repository(session: DBSession) -> PgUserRepository:
    return PgUserRepository(session)


def get_auth_service(
    repo: Annotated[PgUserRepository, Depends(get_user_repository)],
) -> AuthService:
    return AuthService(repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
    repo: Annotated[PgUserRepository, Depends(get_user_repository)],
) -> UserModel:
    if credentials is None:
        raise UnauthorizedException("Thiếu access token")
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise UnauthorizedException(str(exc)) from exc

    user = await repo.get_by_id(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedException("Người dùng không tồn tại hoặc đã bị khoá")
    return user


CurrentUserDep = Annotated[UserModel, Depends(get_current_user)]


def require_permission(permission: str) -> Callable[[UserModel], Awaitable[UserModel]]:
    """Dependency factory — 403s unless the current user's permissions include `permission`."""

    async def _check(current_user: CurrentUserDep) -> UserModel:
        if permission not in current_user.permissions:
            raise ForbiddenException(f"Tài khoản không có quyền '{permission}'")
        return current_user

    return _check


def get_rag_service(
    session: DBSession,
    client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
) -> RAGService:
    return RAGService(session=session, embedding_client=client)


def get_document_relation_service(session: DBSession) -> DocumentRelationService:
    return DocumentRelationService(session=session)


def get_guardrail_service() -> GuardrailService:
    return GuardrailService()


def get_prompt_builder() -> PromptBuilder:
    config = PromptConfig(
        max_prompt_tokens=settings.LLM_MAX_PROMPT_TOKENS,
        max_completion_tokens=settings.LLM_MAX_TOKENS,
        max_context_chunks=settings.KI_MAX_CONTEXT_CHUNKS,
        max_citations=settings.KI_MAX_CITATIONS,
    )
    return PromptBuilder(config=config)


def get_deepseek_service() -> DeepSeekService:
    client = DeepSeekClient(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        model=settings.LLM_MODEL,
        timeout=settings.LLM_TIMEOUT,
        retry_count=settings.LLM_RETRY_COUNT,
    )
    return DeepSeekService(
        client=client,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        top_p=settings.LLM_TOP_P,
    )


def get_response_formatter() -> ResponseFormatter:
    return ResponseFormatter()


def get_chat_service(
    rag: Annotated[RAGService, Depends(get_rag_service)],
    relations: Annotated[
        DocumentRelationService, Depends(get_document_relation_service)
    ],
    guardrail: Annotated[GuardrailService, Depends(get_guardrail_service)],
) -> "ChatService":
    from app.services.chat_service import ChatService

    return ChatService(
        rag=rag,
        relations=relations,
        guardrail=guardrail,
        prompt_builder=get_prompt_builder(),
        deepseek_service=get_deepseek_service(),
        response_formatter=get_response_formatter(),
    )


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


# SearchService alias for backward compat in routers
def get_search_service(session: DBSession) -> RAGService:
    return RAGService(session=session, embedding_client=_embedding_client)


def get_knowledge_service(session: DBSession) -> DocumentRelationService:
    return DocumentRelationService(session=session)
