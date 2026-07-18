from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID = Field(description="UUID định danh tài liệu")
    title: str = Field(description="Tiêu đề văn bản")
    filename: str = Field(description="Tên file đã lưu trên server (có hash)")
    original_filename: str = Field(description="Tên file gốc khi upload")
    content_type: str = Field(description="MIME type của file (application/pdf, ...)")
    file_size: int = Field(description="Kích thước file tính bằng byte")
    file_path: str = Field(description="Đường dẫn file trên server")
    content_hash: str = Field(description="SHA-256 nội dung file — dùng để phát hiện file trùng lặp")
    status: DocumentStatus = Field(description="Trạng thái xử lý: PENDING / PROCESSING / READY / ERROR")
    version: int = Field(description="Phiên bản tài liệu — tăng mỗi lần cập nhật metadata")
    doc_type: DocumentType = Field(
        description=(
            "Loại văn bản pháp lý:\n"
            "- `LAW` — Luật\n"
            "- `CIRCULAR` — Thông tư\n"
            "- `DECREE` — Nghị định\n"
            "- `DECISION` — Quyết định\n"
            "- `POLICY` — Chính sách nội bộ\n"
            "- `SOP` — Quy trình nghiệp vụ\n"
            "- `FAQ` — Hỏi đáp thường gặp\n"
            "- `PRODUCT_DOC` — Tài liệu sản phẩm\n"
            "- `MANUAL` — Sổ tay hướng dẫn"
        )
    )
    authority_level: AuthorityLevel = Field(
        description=(
            "Cấp thẩm quyền ban hành:\n"
            "- `NATIONAL_LAW` — Luật Quốc hội ban hành\n"
            "- `NHNN_CIRCULAR` — Thông tư Ngân hàng Nhà nước\n"
            "- `NHNN_DECISION` — Quyết định Ngân hàng Nhà nước\n"
            "- `INTERNAL_POLICY` — Chính sách nội bộ ngân hàng\n"
            "- `DEPARTMENT_SOP` — Quy trình cấp phòng ban\n"
            "- `FAQ` — Tài liệu hỏi đáp"
        )
    )
    doc_number: str | None = Field(description="Số hiệu văn bản, ví dụ: 36/2014/TT-NHNN")
    issuing_body: str | None = Field(description="Cơ quan ban hành, ví dụ: Ngân hàng Nhà nước Việt Nam")
    issued_date: date | None = Field(description="Ngày ban hành văn bản")
    effective_date: date | None = Field(description="Ngày văn bản có hiệu lực")
    expired_date: date | None = Field(description="Ngày văn bản hết hiệu lực (null nếu chưa hết hạn)")
    tags: list[str] = Field(description="Danh sách nhãn phân loại tự do")
    metadata_extra: dict[str, Any] = Field(description="Metadata bổ sung tuỳ chỉnh dưới dạng JSON")
    created_at: datetime = Field(description="Thời điểm tạo bản ghi (UTC)")
    updated_at: datetime = Field(description="Thời điểm cập nhật lần cuối (UTC)")
    deleted_at: datetime | None = Field(description="Thời điểm xoá mềm — null nếu tài liệu chưa bị xoá")


class DocumentUpdateRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    title: str | None = Field(None, min_length=1, max_length=500, description="Tiêu đề mới")
    doc_number: str | None = Field(None, max_length=100, description="Số hiệu văn bản mới")
    doc_type: DocumentType | None = Field(
        None,
        description=(
            "Loại văn bản mới:\n"
            "- `LAW` — Luật\n"
            "- `CIRCULAR` — Thông tư\n"
            "- `DECREE` — Nghị định\n"
            "- `DECISION` — Quyết định\n"
            "- `POLICY` — Chính sách nội bộ\n"
            "- `SOP` — Quy trình nghiệp vụ\n"
            "- `FAQ` — Hỏi đáp thường gặp\n"
            "- `PRODUCT_DOC` — Tài liệu sản phẩm\n"
            "- `MANUAL` — Sổ tay hướng dẫn"
        ),
    )
    authority_level: AuthorityLevel | None = Field(
        None,
        description=(
            "Cấp thẩm quyền mới:\n"
            "- `NATIONAL_LAW` — Luật Quốc hội ban hành\n"
            "- `NHNN_CIRCULAR` — Thông tư Ngân hàng Nhà nước\n"
            "- `NHNN_DECISION` — Quyết định Ngân hàng Nhà nước\n"
            "- `INTERNAL_POLICY` — Chính sách nội bộ ngân hàng\n"
            "- `DEPARTMENT_SOP` — Quy trình cấp phòng ban\n"
            "- `FAQ` — Tài liệu hỏi đáp"
        ),
    )
    issuing_body: str | None = Field(None, max_length=200, description="Cơ quan ban hành mới")
    issued_date: date | None = Field(None, description="Ngày ban hành mới")
    effective_date: date | None = Field(None, description="Ngày hiệu lực mới")
    expired_date: date | None = Field(None, description="Ngày hết hiệu lực mới")
    status: DocumentStatus | None = Field(None, description="Trạng thái mới")
    tags: list[str] | None = Field(None, description="Danh sách nhãn mới — thay thế hoàn toàn danh sách cũ")
    metadata_extra: dict[str, Any] | None = Field(None, description="Metadata bổ sung mới — thay thế hoàn toàn")
