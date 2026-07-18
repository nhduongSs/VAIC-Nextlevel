from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.value_objects.embedding_status import EmbeddingStatus


class EmbeddingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID = Field(description="UUID định danh embedding job")
    document_id: UUID = Field(description="UUID tài liệu được embed")
    status: EmbeddingStatus = Field(
        description="Trạng thái job: PENDING / RUNNING / COMPLETED / FAILED / RETRYING / CANCELLED"
    )
    model_name: str = Field(description="Tên model embedding đã dùng, ví dụ: BAAI/bge-m3")
    total_chunks: int = Field(description="Tổng số chunk cần tạo vector embedding")
    embedded_chunks: int = Field(description="Số chunk đã embed thành công")
    failed_chunks: int = Field(description="Số chunk thất bại (lỗi HTTP hoặc timeout)")
    retry_count: int = Field(description="Số lần job đã thử lại do lỗi")
    progress_pct: float = Field(description="Tiến độ embed tính theo phần trăm (0.0 - 100.0)")
    started_at: datetime | None = Field(
        description="Thời điểm job bắt đầu chạy (UTC) — null nếu chưa start"
    )
    completed_at: datetime | None = Field(
        description="Thời điểm job hoàn thành (UTC) — null nếu đang chạy"
    )
    error_message: str | None = Field(
        description="Thông báo lỗi nếu job kết thúc với trạng thái FAILED"
    )
    created_at: datetime = Field(description="Thời điểm job được tạo (UTC)")


class EmbeddingStatusResponse(BaseModel):
    document_id: UUID = Field(description="UUID tài liệu")
    job_id: UUID | None = Field(
        description="UUID job embedding mới nhất — null nếu chưa có job nào"
    )
    status: EmbeddingStatus | None = Field(
        description="Trạng thái job mới nhất — null nếu chưa có job"
    )
    progress_pct: float = Field(description="Tiến độ hiện tại tính theo phần trăm (0.0 - 100.0)")
    embedded_chunks: int = Field(description="Số chunk đã có vector embedding")
    total_chunks: int = Field(description="Tổng số chunk của tài liệu")
    model_name: str | None = Field(description="Tên model đang được dùng — null nếu chưa có job")
