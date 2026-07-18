"""Retrieval + KI endpoints — from presentation/routers/retrieve_router.py."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_knowledge_service, get_search_service
from app.models.schemas import (
    CitationResponse,
    ConflictResponse,
    ContextChunk,
    RelationshipResponse,
    RetrieveContextResponse,
    RetrieveHealthResponse,
    RetrievePreviewResponse,
    RetrieveRequest,
    SearchResultItem,
    TimelineEntryResponse,
)
from app.repositories.vector_store import SearchFilters as SearchFiltersDTO
from app.repositories.vector_store import SearchRequest as SearchRequestDTO
from app.services.document_relation_service import DocumentRelationService
from app.services.rag_service import RAGService
from app.utils.constants import API_V1_PREFIX

router = APIRouter(prefix=f"{API_V1_PREFIX}/retrieve", tags=["Retrieve"])

SearchServiceDep = Annotated[RAGService, Depends(get_search_service)]
KIServiceDep = Annotated[DocumentRelationService, Depends(get_knowledge_service)]


@router.post(
    "/context",
    response_model=RetrieveContextResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieval + Knowledge Intelligence → ContextPackage",
    description=(
        "Chạy toàn bộ pipeline: Hybrid Search → Authority Ranking → Version Resolution "
        "→ Conflict Detection → Relationship Expansion → Citation Builder → Timeline Builder "
        "→ Context Assembly."
    ),
)
async def retrieve_context(
    body: RetrieveRequest,
    search_svc: SearchServiceDep,
    ki_svc: KIServiceDep,
) -> RetrieveContextResponse:
    results = await search_svc.search(_to_search_dto(body))
    package = await ki_svc.process(body.query, results)
    return _package_to_response(package)


@router.post(
    "/preview",
    response_model=RetrievePreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve + KI với raw retrieval để debug",
)
async def retrieve_preview(
    body: RetrieveRequest,
    search_svc: SearchServiceDep,
    ki_svc: KIServiceDep,
) -> RetrievePreviewResponse:
    results = await search_svc.search(_to_search_dto(body))
    package = await ki_svc.process(body.query, results)
    base = _package_to_response(package)
    return RetrievePreviewResponse(
        **base.model_dump(),
        raw_retrieval=[
            SearchResultItem(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                content=r.content,
                score=round(r.score, 6),
                retrieval_method=r.retrieval_method,
                chunk_index=r.chunk_index,
                chunk_type=r.chunk_type,
                section_title=r.section_title,
                section_number=r.section_number,
                page_number=r.page_number,
                metadata=r.metadata,
            )
            for r in results
        ],
    )


@router.get(
    "/health",
    response_model=RetrieveHealthResponse,
    summary="Kiểm tra trạng thái Knowledge Intelligence pipeline",
)
async def retrieve_health(ki_svc: KIServiceDep) -> RetrieveHealthResponse:
    db_ok = await ki_svc.health()
    return RetrieveHealthResponse(
        status="ok" if db_ok else "degraded",
        database=db_ok,
        message="KI pipeline ready" if db_ok else "Database unavailable",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_search_dto(body: RetrieveRequest) -> SearchRequestDTO:
    filters: SearchFiltersDTO | None = None
    if body.filters:
        f = body.filters
        filters = SearchFiltersDTO(
            doc_type=f.doc_type.value if f.doc_type else None,
            authority_level=f.authority_level.value if f.authority_level else None,
            department=f.department,
            language=f.language,
            version=f.version,
            effective_date_from=f.effective_date_from,
            effective_date_to=f.effective_date_to,
            tags=list(f.tags),
            document_ids=list(f.document_ids),
            bank=f.bank,
            category=f.category,
        )
    return SearchRequestDTO(
        query=body.query,
        top_k=body.top_k,
        filters=filters,
        vector_weight=body.vector_weight,
        bm25_weight=body.bm25_weight,
    )


def _package_to_response(pkg: Any) -> RetrieveContextResponse:
    return RetrieveContextResponse(
        query=pkg.query,
        context=[
            ContextChunk(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                content=r.content,
                score=round(r.score, 6),
                retrieval_method=r.retrieval_method,
                chunk_index=r.chunk_index,
                chunk_type=r.chunk_type,
                section_title=r.section_title,
                section_number=r.section_number,
                page_number=r.page_number,
                bank=r.bank,
                category=r.category,
                metadata=r.metadata,
            )
            for r in pkg.ranked_chunks
        ],
        citations=[
            CitationResponse(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_title=c.document_title,
                doc_number=c.doc_number,
                section_title=c.section_title,
                section_number=c.section_number,
                page_number=c.page_number,
                chunk_index=c.chunk_index,
                authority_level=c.authority_level,
                version=c.version,
                effective_date=c.effective_date,
                content_preview=c.content_preview,
            )
            for c in pkg.citations
        ],
        relationships=[
            RelationshipResponse(
                source_doc_id=r.source_doc_id,
                target_doc_id=r.target_doc_id,
                relation_type=r.relation_type.value,
                confidence=r.confidence,
                description=r.description,
            )
            for r in pkg.relationships
        ],
        conflicts=[
            ConflictResponse(
                source_doc_id=c.source_doc_id,
                target_doc_id=c.target_doc_id,
                source_title=c.source_title,
                target_title=c.target_title,
                description=c.description,
                confidence=c.confidence,
            )
            for c in pkg.conflicts
        ],
        timeline=[
            TimelineEntryResponse(
                document_id=t.document_id,
                document_title=t.document_title,
                doc_number=t.doc_number,
                version=t.version,
                effective_date=t.effective_date,
                issued_date=t.issued_date,
                relation_type=t.relation_type,
                is_current=t.is_current,
            )
            for t in pkg.timeline
        ],
        statistics=pkg.statistics,
    )
