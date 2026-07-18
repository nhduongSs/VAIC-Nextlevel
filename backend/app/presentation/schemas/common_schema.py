from datetime import UTC, datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    field: str | None = Field(None, description="Tên field gây lỗi (null nếu lỗi không gắn với field cụ thể)")
    message: str = Field(description="Mô tả lỗi")


class ErrorResponse(BaseModel):
    error: str = Field(description="Mã lỗi dạng SCREAMING_SNAKE_CASE, ví dụ: NOT_FOUND, VALIDATION_ERROR")
    message: str = Field(description="Thông báo lỗi dạng đọc được")
    request_id: str | None = Field(None, description="ID request để tra cứu log (lấy từ header X-Request-ID)")
    details: list[ErrorDetail] = Field(default_factory=list, description="Danh sách lỗi chi tiết theo từng field (chủ yếu cho lỗi validation)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="Thời điểm xảy ra lỗi (UTC ISO-8601)")


class HealthResponse(BaseModel):
    status: str = Field(description="Trạng thái hệ thống: ok hoặc degraded")
    version: str = Field(description="Phiên bản API")
    environment: str = Field(description="Môi trường đang chạy: development / staging / production")
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
