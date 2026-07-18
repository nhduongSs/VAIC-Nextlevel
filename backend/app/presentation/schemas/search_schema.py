from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import settings
from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_type import DocumentType


class SearchFiltersRequest(BaseModel):
    doc_type: DocumentType | None = Field(None, description="Lọc theo loại văn bản")
    authority_level: AuthorityLevel | None = Field(None, description="Lọc theo cấp thẩm quyền")
    department: str | None = Field(None, max_length=100, description="Lọc theo phòng ban sở hữu")
    language: str | None = Field(
        None, max_length=10, description="Lọc theo ngôn ngữ, ví dụ: vi, en"
    )
    version: int | None = Field(None, ge=1, description="Lọc theo phiên bản tài liệu")
    effective_date_from: date | None = Field(None, description="Ngày hiệu lực từ (YYYY-MM-DD)")
    effective_date_to: date | None = Field(None, description="Ngày hiệu lực đến (YYYY-MM-DD)")
    tags: list[str] = Field(default_factory=list, description="Lọc theo nhãn văn bản (AND)")
    document_ids: list[UUID] = Field(
        default_factory=list, description="Giới hạn tìm kiếm trong danh sách tài liệu"
    )


class SearchRequest(BaseModel):
    query: str = Field(description="Câu truy vấn tìm kiếm", min_length=1, max_length=1000)
    top_k: int = Field(
        default=settings.SEARCH_DEFAULT_TOP_K,
        ge=1,
        le=settings.SEARCH_MAX_TOP_K,
        description=f"Số kết quả trả về (tối đa {settings.SEARCH_MAX_TOP_K})",
    )
    filters: SearchFiltersRequest | None = Field(None, description="Bộ lọc metadata (tuỳ chọn)")
    vector_weight: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description=f"Trọng số vector search (mặc định {settings.SEARCH_HYBRID_ALPHA})",
    )
    bm25_weight: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description=f"Trọng số BM25 search (mặc định {settings.SEARCH_HYBRID_BETA})",
    )

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def validate_weights(self) -> SearchRequest:
        vw = self.vector_weight
        bw = self.bm25_weight
        if vw is not None and bw is not None:
            total = round(vw + bw, 6)
            if total <= 0.0 or total > 1.0:
                raise ValueError(
                    f"vector_weight + bm25_weight = {total} must be greater than 0 and at most 1.0"
                )
        return self


class SearchResultItem(BaseModel):
    chunk_id: UUID = Field(description="UUID của chunk")
    document_id: UUID = Field(description="UUID tài liệu chứa chunk")
    content: str = Field(description="Nội dung văn bản của chunk")
    score: float = Field(description="Điểm relevance tổng hợp (0.0 - 1.0)")
    retrieval_method: str = Field(description="Phương pháp tìm kiếm: bm25 | vector | hybrid")
    chunk_index: int = Field(description="Vị trí chunk trong tài liệu")
    chunk_type: str = Field(description="Loại chunk")
    section_title: str | None = Field(None, description="Tiêu đề mục chứa chunk")
    section_number: str | None = Field(None, description="Số mục")
    page_number: int | None = Field(None, description="Số trang")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata bổ sung")


class SearchResultItemDebug(SearchResultItem):
    bm25_score: float | None = Field(None, description="Điểm BM25 (đã chuẩn hoá 0-1)")
    vector_score: float | None = Field(
        None, description="Điểm cosine similarity (đã chuẩn hoá 0-1)"
    )


class SearchResponse(BaseModel):
    query: str = Field(description="Câu truy vấn gốc")
    total: int = Field(description="Tổng số kết quả trả về")
    results: list[SearchResultItem] = Field(
        description="Danh sách chunks liên quan theo thứ tự độ phù hợp"
    )


class SearchPreviewResponse(BaseModel):
    query: str = Field(description="Câu truy vấn gốc")
    total: int = Field(description="Tổng số kết quả")
    vector_weight: float = Field(description="Trọng số vector search đã dùng")
    bm25_weight: float = Field(description="Trọng số BM25 đã dùng")
    results: list[SearchResultItemDebug] = Field(
        description="Kết quả kèm điểm BM25 và vector riêng biệt"
    )


class SearchHealthResponse(BaseModel):
    status: str = Field(description="ok hoặc degraded")
    embedding_provider: bool = Field(description="Embedding service có kết nối được không")
    message: str = Field(description="Thông báo trạng thái")
