from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.value_objects.chunk_type import ChunkType
from app.domain.value_objects.ingestion_status import IngestionStatus
from app.domain.value_objects.relation_type import RelationType


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID = Field(description="UUID định danh chunk")
    document_id: UUID = Field(description="UUID tài liệu chứa chunk này")
    content: str = Field(description="Nội dung văn bản của chunk")
    chunk_index: int = Field(description="Thứ tự chunk trong tài liệu (bắt đầu từ 0)")
    chunk_type: ChunkType = Field(description="Loại chunk: paragraph, table, header, list_item...")
    page_number: int | None = Field(description="Số trang trong tài liệu gốc (null nếu không xác định)")
    section_title: str | None = Field(description="Tiêu đề mục chứa chunk (null nếu không có)")
    section_number: str | None = Field(description="Số mục theo cấu trúc văn bản, ví dụ: 1.2.3")
    token_count: int | None = Field(description="Số token ước tính (dùng để kiểm soát context window)")
    metadata_extra: dict[str, Any] = Field(description="Metadata bổ sung từ quá trình trích xuất")
    created_at: datetime = Field(description="Thời điểm tạo chunk (UTC)")


class DocumentRelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID = Field(description="UUID định danh quan hệ")
    source_doc_id: UUID = Field(description="UUID tài liệu nguồn (tài liệu tham chiếu)")
    target_doc_id: UUID = Field(description="UUID tài liệu đích (tài liệu được tham chiếu)")
    relation_type: RelationType = Field(description="Loại quan hệ: amends, supersedes, references, implements...")
    confidence: float = Field(description="Độ tin cậy nhận diện quan hệ (0.0 – 1.0)")
    description: str | None = Field(description="Mô tả chi tiết quan hệ (null nếu không có)")
    metadata_extra: dict[str, Any] = Field(description="Metadata bổ sung từ quá trình nhận diện")
    created_at: datetime = Field(description="Thời điểm tạo quan hệ (UTC)")


class ProcessingStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID = Field(description="UUID log xử lý")
    document_id: UUID = Field(description="UUID tài liệu đang được xử lý")
    status: IngestionStatus = Field(description="Trạng thái pipeline: PENDING / RUNNING / COMPLETED / FAILED")
    current_stage: str | None = Field(description="Giai đoạn đang chạy: extract / chunk / detect_relations (null nếu chưa bắt đầu hoặc đã xong)")
    started_at: datetime = Field(description="Thời điểm pipeline bắt đầu chạy (UTC)")
    completed_at: datetime | None = Field(description="Thời điểm pipeline hoàn thành — null nếu đang chạy")
    error_message: str | None = Field(description="Thông báo lỗi nếu pipeline thất bại")
    stage_results: dict[str, Any] = Field(description="Kết quả chi tiết từng giai đoạn (số chunk, số quan hệ...)")
    retry_count: int = Field(description="Số lần pipeline đã thử lại")
    created_at: datetime = Field(description="Thời điểm tạo log (UTC)")


class TriggerProcessingResponse(BaseModel):
    document_id: UUID = Field(description="UUID tài liệu vừa được kích hoạt xử lý")
    message: str = Field(description="Thông báo xác nhận")
