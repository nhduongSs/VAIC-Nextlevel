from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.application.dto.search_dto import SearchFilters
from app.application.dto.search_dto import SearchRequest as SearchRequestDTO
from app.application.services.search_service import SearchService
from app.config import settings
from app.presentation.schemas.search_schema import (
    SearchHealthResponse,
    SearchPreviewResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SearchResultItemDebug,
)
from app.utils.constants import API_V1_PREFIX

router = APIRouter(prefix=f"{API_V1_PREFIX}/search", tags=["Search"])


# ── Dependency stubs (overridden in main.py) ──────────────────────────────────


def _get_search_service() -> SearchService:  # pragma: no cover
    raise NotImplementedError


SearchServiceDep = Annotated[SearchService, Depends(_get_search_service)]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Tìm kiếm văn bản pháp lý (Hybrid BM25 + Vector)",
    description=(
        "Thực hiện tìm kiếm hybrid: kết hợp BM25 (full-text PostgreSQL tsvector) "
        "và Vector Search (pgvector HNSW cosine similarity) với trọng số có thể điều chỉnh.\n\n"
        "Kết quả được sắp xếp theo điểm tổng hợp: "
        "`score = vector_weight * vector_score + bm25_weight * bm25_score`."
    ),
)
async def search(
    body: SearchRequest,
    svc: SearchServiceDep,
) -> SearchResponse:
    request = _to_dto(body)
    results = await svc.search(request)
    return SearchResponse(
        query=body.query,
        total=len(results),
        results=[
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


@router.post(
    "/preview",
    response_model=SearchPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem trước kết quả tìm kiếm kèm điểm thành phần",
    description=(
        "Giống `/search` nhưng trả về thêm `bm25_score` và `vector_score`"
        " riêng biệt cho mỗi kết quả."
        " Dùng để debug, calibrate trọng số, và đánh giá chất lượng retrieval."
    ),
)
async def search_preview(
    body: SearchRequest,
    svc: SearchServiceDep,
) -> SearchPreviewResponse:
    request = _to_dto(body)
    results = await svc.search(request)
    alpha = body.vector_weight if body.vector_weight is not None else settings.SEARCH_HYBRID_ALPHA
    beta = body.bm25_weight if body.bm25_weight is not None else settings.SEARCH_HYBRID_BETA
    return SearchPreviewResponse(
        query=body.query,
        total=len(results),
        vector_weight=alpha,
        bm25_weight=beta,
        results=[
            SearchResultItemDebug(
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
                bm25_score=round(r.bm25_score, 6) if r.bm25_score is not None else None,
                vector_score=round(r.vector_score, 6) if r.vector_score is not None else None,
            )
            for r in results
        ],
    )


@router.get(
    "/health",
    response_model=SearchHealthResponse,
    summary="Kiểm tra trạng thái retrieval pipeline",
    description="Kiểm tra kết nối tới embedding service. Trả về `status=ok` nếu mọi thứ sẵn sàng.",
)
async def search_health(svc: SearchServiceDep) -> SearchHealthResponse:
    provider_ok = await svc.health()
    return SearchHealthResponse(
        status="ok" if provider_ok else "degraded",
        embedding_provider=provider_ok,
        message="Retrieval pipeline ready" if provider_ok else "Embedding service unavailable",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_dto(body: SearchRequest) -> SearchRequestDTO:
    filters: SearchFilters | None = None
    if body.filters:
        f = body.filters
        filters = SearchFilters(
            doc_type=f.doc_type.value if f.doc_type else None,
            authority_level=f.authority_level.value if f.authority_level else None,
            department=f.department,
            language=f.language,
            version=f.version,
            effective_date_from=f.effective_date_from,
            effective_date_to=f.effective_date_to,
            tags=list(f.tags),
            document_ids=list(f.document_ids),
        )
    return SearchRequestDTO(
        query=body.query,
        top_k=body.top_k,
        filters=filters,
        vector_weight=body.vector_weight,
        bm25_weight=body.bm25_weight,
    )
