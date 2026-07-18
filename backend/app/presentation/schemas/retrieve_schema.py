from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import settings
from app.presentation.schemas.search_schema import SearchFiltersRequest, SearchResultItem


class RetrieveRequest(BaseModel):
    query: str = Field(description="Câu truy vấn tìm kiếm", min_length=1, max_length=1000)
    top_k: int = Field(
        default=settings.SEARCH_DEFAULT_TOP_K,
        ge=1,
        le=settings.SEARCH_MAX_TOP_K,
        description="Số chunks retrieval đầu vào cho pipeline KI",
    )
    filters: SearchFiltersRequest | None = Field(None, description="Bộ lọc metadata (tuỳ chọn)")
    vector_weight: float | None = Field(None, ge=0.0, le=1.0)
    bm25_weight: float | None = Field(None, ge=0.0, le=1.0)

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def validate_weights(self) -> RetrieveRequest:
        vw = self.vector_weight
        bw = self.bm25_weight
        if vw is not None and bw is not None:
            total = round(vw + bw, 6)
            if total <= 0.0 or total > 1.0:
                raise ValueError(f"vector_weight + bm25_weight = {total} must be > 0 and ≤ 1.0")
        return self


class CitationResponse(BaseModel):
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


class TimelineEntryResponse(BaseModel):
    document_id: UUID
    document_title: str
    doc_number: str | None
    version: int
    effective_date: date | None
    issued_date: date | None
    relation_type: str | None
    is_current: bool


class ConflictResponse(BaseModel):
    source_doc_id: UUID
    target_doc_id: UUID
    source_title: str
    target_title: str
    description: str | None
    confidence: float


class RelationshipResponse(BaseModel):
    source_doc_id: UUID
    target_doc_id: UUID
    relation_type: str
    confidence: float
    description: str | None


class ContextChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float
    retrieval_method: str
    chunk_index: int
    chunk_type: str
    section_title: str | None
    section_number: str | None
    page_number: int | None
    metadata: dict[str, Any]


class RetrieveContextResponse(BaseModel):
    query: str = Field(description="Câu truy vấn gốc")
    context: list[ContextChunk] = Field(description="Chunks đã xếp hạng sau pipeline KI")
    citations: list[CitationResponse] = Field(description="Danh sách trích dẫn")
    relationships: list[RelationshipResponse] = Field(description="Quan hệ giữa các tài liệu")
    conflicts: list[ConflictResponse] = Field(description="Xung đột phát hiện được")
    timeline: list[TimelineEntryResponse] = Field(description="Lịch sử phiên bản văn bản")
    statistics: dict[str, Any] = Field(description="Số liệu thống kê pipeline")


class RetrievePreviewResponse(RetrieveContextResponse):
    raw_retrieval: list[SearchResultItem] = Field(
        description="Kết quả retrieval gốc trước khi qua KI pipeline"
    )


class RetrieveHealthResponse(BaseModel):
    status: str = Field(description="ok hoặc degraded")
    database: bool = Field(description="Kết nối database")
    message: str = Field(description="Thông báo trạng thái")
