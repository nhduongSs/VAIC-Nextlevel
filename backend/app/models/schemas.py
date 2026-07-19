"""All Pydantic API schemas merged from presentation/schemas/ plus chat schemas."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import settings
from app.models.enums import (
    AuthorityLevel,
    ChunkType,
    DocumentStatus,
    DocumentType,
    EmbeddingStatus,
    IngestionStatus,
    RelationType,
)

T = TypeVar("T")

# ── Common ────────────────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    field: str | None = Field(
        None, description="Tên field gây lỗi (null nếu lỗi không gắn với field cụ thể)"
    )
    message: str = Field(description="Mô tả lỗi")


class ErrorResponse(BaseModel):
    error: str = Field(
        description="Mã lỗi dạng SCREAMING_SNAKE_CASE, ví dụ: NOT_FOUND, VALIDATION_ERROR"
    )
    message: str = Field(description="Thông báo lỗi dạng đọc được")
    request_id: str | None = Field(
        None, description="ID request để tra cứu log (lấy từ header X-Request-ID)"
    )
    details: list[ErrorDetail] = Field(
        default_factory=list,
        description="Danh sách lỗi chi tiết theo từng field (chủ yếu cho lỗi validation)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="Thời điểm xảy ra lỗi (UTC ISO-8601)",
    )


class HealthResponse(BaseModel):
    status: str = Field(description="Trạng thái hệ thống: ok hoặc degraded")
    version: str = Field(description="Phiên bản API")
    environment: str = Field(
        description="Môi trường đang chạy: development / staging / production"
    )
    timestamp: datetime = Field(description="Thời điểm kiểm tra health (UTC)")


class PaginationMeta(BaseModel):
    total: int = Field(description="Tổng số bản ghi khớp điều kiện lọc")
    limit: int = Field(description="Số bản ghi tối đa trả về trong trang này")
    offset: int = Field(description="Vị trí bắt đầu (số bản ghi đã bỏ qua)")
    has_next: bool = Field(description="Còn trang tiếp theo không")
    has_prev: bool = Field(description="Có trang trước không")


class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: list[T] = Field(description="Danh sách kết quả của trang hiện tại")
    meta: PaginationMeta = Field(description="Thông tin phân trang")


class IDResponse(BaseModel):
    id: UUID = Field(description="UUID của bản ghi vừa tạo")


class MessageResponse(BaseModel):
    message: str = Field(description="Thông báo kết quả")


class OKResponse(BaseModel):
    ok: bool = Field(True, description="True nếu thao tác thành công")


# ── Document ──────────────────────────────────────────────────────────────────


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID = Field(description="UUID định danh tài liệu")
    title: str = Field(description="Tiêu đề văn bản")
    filename: str = Field(description="Tên file đã lưu trên server (có hash)")
    original_filename: str = Field(description="Tên file gốc khi upload")
    content_type: str = Field(description="MIME type của file (application/pdf, ...)")
    file_size: int = Field(description="Kích thước file tính bằng byte")
    file_path: str = Field(description="Đường dẫn file trên server")
    content_hash: str = Field(
        description="SHA-256 nội dung file — dùng để phát hiện file trùng lặp"
    )
    status: DocumentStatus = Field(
        description="Trạng thái xử lý: PENDING / PROCESSING / READY / ERROR"
    )
    version: int = Field(
        description="Phiên bản tài liệu — tăng mỗi lần cập nhật metadata"
    )
    doc_type: DocumentType = Field(description="Loại văn bản pháp lý")
    authority_level: AuthorityLevel = Field(description="Cấp thẩm quyền ban hành")
    doc_number: str | None = Field(
        description="Số hiệu văn bản, ví dụ: 36/2014/TT-NHNN"
    )
    issuing_body: str | None = Field(
        description="Cơ quan ban hành, ví dụ: Ngân hàng Nhà nước Việt Nam"
    )
    issued_date: date | None = Field(description="Ngày ban hành văn bản")
    effective_date: date | None = Field(description="Ngày văn bản có hiệu lực")
    expired_date: date | None = Field(
        description="Ngày văn bản hết hiệu lực (null nếu chưa hết hạn)"
    )
    tags: list[str] = Field(description="Danh sách nhãn phân loại tự do")
    metadata_extra: dict[str, Any] = Field(
        description="Metadata bổ sung tuỳ chỉnh dưới dạng JSON"
    )
    created_at: datetime = Field(description="Thời điểm tạo bản ghi (UTC)")
    updated_at: datetime = Field(description="Thời điểm cập nhật lần cuối (UTC)")
    deleted_at: datetime | None = Field(
        description="Thời điểm xoá mềm — null nếu tài liệu chưa bị xoá"
    )


class DocumentUpdateRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    title: str | None = Field(
        None, min_length=1, max_length=500, description="Tiêu đề mới"
    )
    doc_number: str | None = Field(
        None, max_length=100, description="Số hiệu văn bản mới"
    )
    doc_type: DocumentType | None = Field(None, description="Loại văn bản mới")
    authority_level: AuthorityLevel | None = Field(
        None, description="Cấp thẩm quyền mới"
    )
    issuing_body: str | None = Field(
        None, max_length=200, description="Cơ quan ban hành mới"
    )
    issued_date: date | None = Field(None, description="Ngày ban hành mới")
    effective_date: date | None = Field(None, description="Ngày hiệu lực mới")
    expired_date: date | None = Field(None, description="Ngày hết hiệu lực mới")
    status: DocumentStatus | None = Field(None, description="Trạng thái mới")
    tags: list[str] | None = Field(
        None, description="Danh sách nhãn mới — thay thế hoàn toàn danh sách cũ"
    )
    metadata_extra: dict[str, Any] | None = Field(
        None, description="Metadata bổ sung mới — thay thế hoàn toàn"
    )


# ── Embedding ─────────────────────────────────────────────────────────────────


class EmbeddingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID = Field(description="UUID định danh embedding job")
    document_id: UUID = Field(description="UUID tài liệu được embed")
    status: EmbeddingStatus = Field(description="Trạng thái job")
    model_name: str = Field(description="Tên model embedding đã dùng")
    total_chunks: int = Field(description="Tổng số chunk cần tạo vector embedding")
    embedded_chunks: int = Field(description="Số chunk đã embed thành công")
    failed_chunks: int = Field(description="Số chunk thất bại")
    retry_count: int = Field(description="Số lần job đã thử lại do lỗi")
    progress_pct: float = Field(
        description="Tiến độ embed tính theo phần trăm (0.0 - 100.0)"
    )
    started_at: datetime | None = Field(description="Thời điểm job bắt đầu chạy (UTC)")
    completed_at: datetime | None = Field(description="Thời điểm job hoàn thành (UTC)")
    error_message: str | None = Field(
        description="Thông báo lỗi nếu job kết thúc với FAILED"
    )
    created_at: datetime = Field(description="Thời điểm job được tạo (UTC)")


class EmbeddingStatusResponse(BaseModel):
    document_id: UUID = Field(description="UUID tài liệu")
    job_id: UUID | None = Field(description="UUID job embedding mới nhất")
    status: EmbeddingStatus | None = Field(description="Trạng thái job mới nhất")
    progress_pct: float = Field(
        description="Tiến độ hiện tại tính theo phần trăm (0.0 - 100.0)"
    )
    embedded_chunks: int = Field(description="Số chunk đã có vector embedding")
    total_chunks: int = Field(description="Tổng số chunk của tài liệu")
    model_name: str | None = Field(description="Tên model đang được dùng")


# ── Ingestion ─────────────────────────────────────────────────────────────────


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID = Field(description="UUID định danh chunk")
    document_id: UUID = Field(description="UUID tài liệu chứa chunk này")
    content: str = Field(description="Nội dung văn bản của chunk")
    chunk_index: int = Field(description="Thứ tự chunk trong tài liệu (bắt đầu từ 0)")
    chunk_type: ChunkType = Field(description="Loại chunk")
    page_number: int | None = Field(description="Số trang trong tài liệu gốc")
    section_title: str | None = Field(description="Tiêu đề mục chứa chunk")
    section_number: str | None = Field(description="Số mục theo cấu trúc văn bản")
    token_count: int | None = Field(description="Số token ước tính")
    metadata_extra: dict[str, Any] = Field(
        description="Metadata bổ sung từ quá trình trích xuất"
    )
    created_at: datetime = Field(description="Thời điểm tạo chunk (UTC)")


class DocumentRelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID = Field(description="UUID định danh quan hệ")
    source_doc_id: UUID = Field(description="UUID tài liệu nguồn")
    target_doc_id: UUID = Field(description="UUID tài liệu đích")
    relation_type: RelationType = Field(description="Loại quan hệ")
    confidence: float = Field(description="Độ tin cậy nhận diện quan hệ (0.0 - 1.0)")
    description: str | None = Field(description="Mô tả chi tiết quan hệ")
    metadata_extra: dict[str, Any] = Field(
        description="Metadata bổ sung từ quá trình nhận diện"
    )
    created_at: datetime = Field(description="Thời điểm tạo quan hệ (UTC)")


class ProcessingStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID = Field(description="UUID log xử lý")
    document_id: UUID = Field(description="UUID tài liệu đang được xử lý")
    status: IngestionStatus = Field(description="Trạng thái pipeline")
    current_stage: str | None = Field(description="Giai đoạn đang chạy")
    started_at: datetime = Field(description="Thời điểm pipeline bắt đầu chạy (UTC)")
    completed_at: datetime | None = Field(description="Thời điểm pipeline hoàn thành")
    error_message: str | None = Field(description="Thông báo lỗi nếu pipeline thất bại")
    stage_results: dict[str, Any] = Field(description="Kết quả chi tiết từng giai đoạn")
    retry_count: int = Field(description="Số lần pipeline đã thử lại")
    created_at: datetime = Field(description="Thời điểm tạo log (UTC)")


class TriggerProcessingResponse(BaseModel):
    document_id: UUID = Field(description="UUID tài liệu vừa được kích hoạt xử lý")
    message: str = Field(description="Thông báo xác nhận")


# ── Search ────────────────────────────────────────────────────────────────────


class SearchFiltersRequest(BaseModel):
    doc_type: DocumentType | None = Field(None, description="Lọc theo loại văn bản")
    authority_level: AuthorityLevel | None = Field(
        None, description="Lọc theo cấp thẩm quyền"
    )
    department: str | None = Field(
        None, max_length=100, description="Lọc theo phòng ban sở hữu"
    )
    language: str | None = Field(
        None, max_length=10, description="Lọc theo ngôn ngữ, ví dụ: vi, en"
    )
    version: int | None = Field(None, ge=1, description="Lọc theo phiên bản tài liệu")
    effective_date_from: date | None = Field(
        None, description="Ngày hiệu lực từ (YYYY-MM-DD)"
    )
    effective_date_to: date | None = Field(
        None, description="Ngày hiệu lực đến (YYYY-MM-DD)"
    )
    tags: list[str] = Field(
        default_factory=list, description="Lọc theo nhãn văn bản (AND)"
    )
    document_ids: list[UUID] = Field(
        default_factory=list, description="Giới hạn tìm kiếm trong danh sách tài liệu"
    )
    bank: str | None = Field(
        None, max_length=100, description="Lọc theo ngân hàng (SHB, BIDV, VCB, ...)"
    )
    category: str | None = Field(
        None,
        max_length=50,
        description="Lọc theo danh mục: lai_suat | bieu_phi | dieu_khoan | thu_tuc",
    )


class SearchRequest(BaseModel):
    query: str = Field(
        description="Câu truy vấn tìm kiếm", min_length=1, max_length=1000
    )
    top_k: int = Field(
        default=settings.SEARCH_DEFAULT_TOP_K,
        ge=1,
        le=settings.SEARCH_MAX_TOP_K,
        description=f"Số kết quả trả về (tối đa {settings.SEARCH_MAX_TOP_K})",
    )
    filters: SearchFiltersRequest | None = Field(
        None, description="Bộ lọc metadata (tuỳ chọn)"
    )
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
    retrieval_method: str = Field(
        description="Phương pháp tìm kiếm: bm25 | vector | hybrid"
    )
    chunk_index: int = Field(description="Vị trí chunk trong tài liệu")
    chunk_type: str = Field(description="Loại chunk")
    section_title: str | None = Field(None, description="Tiêu đề mục chứa chunk")
    section_number: str | None = Field(None, description="Số mục")
    page_number: int | None = Field(None, description="Số trang")
    bank: str | None = Field(None, description="Ngân hàng sở hữu tài liệu")
    category: str | None = Field(
        None, description="Danh mục: lai_suat | bieu_phi | dieu_khoan | thu_tuc"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata bổ sung"
    )


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
    embedding_provider: bool = Field(
        description="Embedding service có kết nối được không"
    )
    message: str = Field(description="Thông báo trạng thái")


# ── Retrieve ──────────────────────────────────────────────────────────────────


class RetrieveRequest(BaseModel):
    query: str = Field(
        description="Câu truy vấn tìm kiếm", min_length=1, max_length=1000
    )
    top_k: int = Field(
        default=settings.SEARCH_DEFAULT_TOP_K,
        ge=1,
        le=settings.SEARCH_MAX_TOP_K,
        description="Số chunks retrieval đầu vào cho pipeline KI",
    )
    filters: SearchFiltersRequest | None = Field(
        None, description="Bộ lọc metadata (tuỳ chọn)"
    )
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
                raise ValueError(
                    f"vector_weight + bm25_weight = {total} must be > 0 and <= 1.0"
                )
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
    bank: str | None = None
    category: str | None = None
    metadata: dict[str, Any]


class RetrieveContextResponse(BaseModel):
    query: str = Field(description="Câu truy vấn gốc")
    context: list[ContextChunk] = Field(
        description="Chunks đã xếp hạng sau pipeline KI"
    )
    citations: list[CitationResponse] = Field(description="Danh sách trích dẫn")
    relationships: list[RelationshipResponse] = Field(
        description="Quan hệ giữa các tài liệu"
    )
    conflicts: list[ConflictResponse] = Field(description="Xung đột phát hiện được")
    timeline: list[TimelineEntryResponse] = Field(
        description="Lịch sử phiên bản văn bản"
    )
    statistics: dict[str, Any] = Field(description="Số liệu thống kê pipeline")


class RetrievePreviewResponse(RetrieveContextResponse):
    raw_retrieval: list[SearchResultItem] = Field(
        description="Kết quả retrieval gốc trước khi qua KI pipeline"
    )


class RetrieveHealthResponse(BaseModel):
    status: str = Field(description="ok hoặc degraded")
    database: bool = Field(description="Kết nối database")
    message: str = Field(description="Thông báo trạng thái")


# ── Chat ──────────────────────────────────────────────────────────────────────


class BankRateItem(BaseModel):
    term: str = Field(description="Kỳ hạn hiển thị, ví dụ: '12 tháng', 'Không kỳ hạn'")
    term_months: float | None = Field(
        None,
        description="Kỳ hạn dạng số (tháng) để sort/group/nối trực tiếp vào UI — "
        "null cho 'Không kỳ hạn'. Dùng field này thay vì tự parse chuỗi `term`.",
    )
    rate_value: float = Field(description="Lãi suất %/năm")
    currency: str = Field(description="Đơn vị tiền tệ, ví dụ: VND")
    customer_segment: str = Field(description="ca_nhan hoặc doanh_nghiep")
    effective_date: date | None = Field(None, description="Ngày hiệu lực (nếu có)")
    source_url: str | None = Field(None, description="Nguồn công bố lãi suất")


class RateBankResult(BaseModel):
    bank: str = Field(description="Tên ngân hàng")
    rates: list[BankRateItem] = Field(
        description="Số liệu lãi suất thật từ bank_products (SQL, không phải LLM ước lượng)"
    )


class RateComparisonResponse(BaseModel):
    term: str | None = Field(None, description="Kỳ hạn tra cứu, ví dụ: 12 tháng")
    customer_segment: str = Field(description="ca_nhan hoặc doanh_nghiep")
    banks: list[RateBankResult] = Field(description="Kết quả nhóm theo ngân hàng")


class ChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    message: str = Field(..., max_length=4000)


class Source(BaseModel):
    doc_id: str
    title: str
    clause: str
    effective_date: str | None = None
    bank: str | None = None
    doc_class: str | None = None


class ConflictInfo(BaseModel):
    description: str
    conflicting_sources: list[str] = Field(
        description="doc_id của 2 văn bản mâu thuẫn (giữ để tương thích ngược)"
    )
    source_doc_id: str = Field(description="doc_id văn bản thứ nhất")
    source_title: str = Field(description="Tên văn bản thứ nhất — FE hiển thị trực tiếp")
    target_doc_id: str = Field(description="doc_id văn bản thứ hai")
    target_title: str = Field(description="Tên văn bản thứ hai — FE hiển thị trực tiếp")
    confidence: float = Field(description="Độ tin cậy của cảnh báo mâu thuẫn (0-1)")


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[Source] = []
    conflicts: list[ConflictInfo] = []
    timeline: list[TimelineEntryResponse] = Field(
        default_factory=list,
        description="Lịch sử phiên bản văn bản liên quan tới câu trả lời (KI Timeline Builder)",
    )
    blocked: bool = False
    block_reason: str = "none"


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email đăng nhập")
    password: str = Field(..., min_length=1, description="Mật khẩu")


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str = Field(description="ADMIN hoặc STAFF")
    permissions: list[str] = Field(description="Danh sách quyền của user")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Thời gian hết hạn access token (giây)")
    user: UserResponse


# ── Wave 4 — AI Generation schemas ───────────────────────────────────────────


class ChatStreamEvent(BaseModel):
    event: str  # "token" | "done" | "error"
    data: str


class AnswerUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    provider: str
    model: str


class ChatResponseV2(ChatResponse):
    usage: AnswerUsage | None = None
    confidence_score: float | None = None
    latency_ms: float | None = None
    prompt_type: str | None = None


class PromptBuildRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    prompt_type: str = Field(default="qa")
    max_chunks: int = Field(default=10, ge=1, le=20)


class PromptBuildResponse(BaseModel):
    prompt_type: str
    system_prompt: str
    user_prompt: str
    estimated_prompt_tokens: int
    estimated_completion_tokens: int
    estimated_total_tokens: int
    context_chunks_used: int
    was_truncated: bool


class PromptPreviewResponse(PromptBuildResponse):
    config: dict[str, Any]
    optimization_applied: bool
