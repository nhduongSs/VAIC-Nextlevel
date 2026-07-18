"""Search endpoints — from presentation/routers/search_router.py."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.config import settings
from app.core.dependencies import get_bank_product_repository, get_search_service
from app.models.schemas import (
    BankRateItem,
    RateBankResult,
    RateComparisonResponse,
    SearchFiltersRequest,
    SearchHealthResponse,
    SearchPreviewResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SearchResultItemDebug,
)
from app.repositories.bank_product_store import PgBankProductRepository
from app.repositories.vector_store import SearchFilters as SearchFiltersDTO
from app.repositories.vector_store import SearchRequest as SearchRequestDTO
from app.services.rag_service import RAGService
from app.utils.constants import API_V1_PREFIX

router = APIRouter(prefix=f"{API_V1_PREFIX}/search", tags=["Search"])

SearchServiceDep = Annotated[RAGService, Depends(get_search_service)]
BankProductRepoDep = Annotated[
    PgBankProductRepository, Depends(get_bank_product_repository)
]


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Tìm kiếm văn bản pháp lý (Hybrid BM25 + Vector)",
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
                bank=r.bank,
                category=r.category,
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
)
async def search_preview(
    body: SearchRequest,
    svc: SearchServiceDep,
) -> SearchPreviewResponse:
    request = _to_dto(body)
    results = await svc.search(request)
    alpha = (
        body.vector_weight
        if body.vector_weight is not None
        else settings.SEARCH_HYBRID_ALPHA
    )
    beta = (
        body.bm25_weight
        if body.bm25_weight is not None
        else settings.SEARCH_HYBRID_BETA
    )
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
                bank=r.bank,
                category=r.category,
                metadata=r.metadata,
                bm25_score=round(r.bm25_score, 6) if r.bm25_score is not None else None,
                vector_score=round(r.vector_score, 6)
                if r.vector_score is not None
                else None,
            )
            for r in results
        ],
    )


@router.get(
    "/rates/compare",
    response_model=RateComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="So sánh lãi suất giữa các ngân hàng theo kỳ hạn",
    description=(
        "Tra cứu bảng bank_products (Lớp C) bằng SQL chính xác, nhóm kết quả theo "
        "ngân hàng. Số liệu thật (BIDV, Vietcombank, VietinBank, SHB), KHÔNG để LLM "
        "tự so sánh số. Dùng để so sánh lãi suất tiền gửi kỳ hạn X giữa nhiều ngân "
        "hàng (FAQ 2)."
    ),
)
async def compare_rates(
    repo: BankProductRepoDep,
    term: Annotated[
        str | None,
        Query(description="Kỳ hạn cần tra cứu, ví dụ: '12 tháng', '6', '24'"),
    ] = None,
    bank: Annotated[
        str | None,
        Query(description="Giới hạn so sánh trong một ngân hàng cụ thể (tuỳ chọn)"),
    ] = None,
    customer_segment: Annotated[
        str, Query(description="ca_nhan hoặc doanh_nghiep")
    ] = "ca_nhan",
) -> RateComparisonResponse:
    rows = await repo.compare(term=term, customer_segment=customer_segment, bank=bank)

    grouped: dict[str, list[BankRateItem]] = {}
    for row in rows:
        grouped.setdefault(row.bank, []).append(
            BankRateItem(
                term=row.term,
                rate_value=float(row.rate_value),
                currency=row.currency,
                customer_segment=row.customer_segment,
                effective_date=row.effective_date,
                source_url=row.source_url,
            )
        )

    return RateComparisonResponse(
        term=term,
        customer_segment=customer_segment,
        banks=[
            RateBankResult(bank=b, rates=rates) for b, rates in grouped.items()
        ],
    )


@router.get(
    "/health",
    response_model=SearchHealthResponse,
    summary="Kiểm tra trạng thái retrieval pipeline",
)
async def search_health(svc: SearchServiceDep) -> SearchHealthResponse:
    provider_ok = await svc.health()
    return SearchHealthResponse(
        status="ok" if provider_ok else "degraded",
        embedding_provider=provider_ok,
        message="Retrieval pipeline ready"
        if provider_ok
        else "Embedding service unavailable",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_dto(body: SearchRequest) -> SearchRequestDTO:
    filters: SearchFiltersDTO | None = None
    if body.filters:
        f: SearchFiltersRequest = body.filters
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
