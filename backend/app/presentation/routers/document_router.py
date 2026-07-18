from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.application.dto.document_dto import CreateDocumentDTO, UpdateDocumentDTO
from app.application.services.document_service import DocumentService
from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_status import DocumentStatus
from app.domain.value_objects.document_type import DocumentType
from app.presentation.schemas.common_schema import PaginatedResponse, PaginationMeta
from app.presentation.schemas.document_schema import DocumentResponse, DocumentUpdateRequest
from app.utils.constants import API_V1_PREFIX, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix=f"{API_V1_PREFIX}/documents", tags=["Documents"])


def _get_document_service() -> DocumentService:  # pragma: no cover
    # Overridden via app.dependency_overrides at app startup (see app/main.py).
    raise NotImplementedError


DocumentServiceDep = Annotated[DocumentService, Depends(_get_document_service)]


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload tài liệu mới",
    description=(
        "Upload file PDF/DOCX/TXT kèm metadata văn bản pháp lý. "
        "File được lưu vào storage, hash nội dung được tính để phát hiện trùng lặp. "
        "Trả về thông tin tài liệu vừa tạo với trạng thái PENDING."
    ),
)
async def upload_document(
    service: DocumentServiceDep,
    file: Annotated[UploadFile, File(description="File tài liệu cần upload (PDF, DOCX, TXT)")],
    title: Annotated[str, Form(min_length=1, max_length=500, description="Tiêu đề văn bản")],
    doc_type: Annotated[
        DocumentType,
        Form(
            description=(
                "Loại văn bản: LAW=Luật | CIRCULAR=Thông tư | DECREE=Nghị định | "
                "DECISION=Quyết định | POLICY=Chính sách nội bộ | SOP=Quy trình | "
                "FAQ=Hỏi đáp | PRODUCT_DOC=Tài liệu sản phẩm | MANUAL=Sổ tay"
            )
        ),
    ],
    authority_level: Annotated[
        AuthorityLevel,
        Form(
            description=(
                "Cấp thẩm quyền: NATIONAL_LAW=Luật QH | NHNN_CIRCULAR=Thông tư NHNN | "
                "NHNN_DECISION=Quyết định NHNN | INTERNAL_POLICY=Chính sách nội bộ | "
                "DEPARTMENT_SOP=Quy trình phòng ban | FAQ=Hỏi đáp"
            )
        ),
    ],
    doc_number: Annotated[
        str | None, Form(max_length=100, description="Số hiệu văn bản, ví dụ: 36/2014/TT-NHNN")
    ] = None,
    issuing_body: Annotated[
        str | None,
        Form(max_length=200, description="Cơ quan ban hành, ví dụ: Ngân hàng Nhà nước Việt Nam"),
    ] = None,
    issued_date: Annotated[date | None, Form(description="Ngày ban hành (YYYY-MM-DD)")] = None,
    effective_date: Annotated[
        date | None, Form(description="Ngày có hiệu lực (YYYY-MM-DD)")
    ] = None,
    expired_date: Annotated[
        date | None, Form(description="Ngày hết hiệu lực (YYYY-MM-DD) — bỏ trống nếu chưa biết")
    ] = None,
) -> DocumentResponse:
    dto = CreateDocumentDTO(
        title=title,
        doc_type=doc_type,
        authority_level=authority_level,
        doc_number=doc_number,
        issuing_body=issuing_body,
        issued_date=issued_date,
        effective_date=effective_date,
        expired_date=expired_date,
    )

    file_data = await file.read()
    original_filename = file.filename or "unknown"
    content_type = file.content_type or "application/octet-stream"

    document = await service.upload_document(
        file_data=file_data,
        original_filename=original_filename,
        content_type=content_type,
        dto=dto,
    )

    return DocumentResponse.model_validate(document)


@router.get(
    "",
    response_model=PaginatedResponse[DocumentResponse],
    summary="Danh sách tài liệu (có phân trang và lọc)",
    description=(
        "Lấy danh sách tài liệu với phân trang."
        " Có thể lọc theo trạng thái, loại văn bản và tìm kiếm full-text."
    ),
)
async def list_documents(
    service: DocumentServiceDep,
    offset: Annotated[int, Query(ge=0, description="Số bản ghi bỏ qua (dùng cho phân trang)")] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_PAGE_SIZE,
            description=f"Số bản ghi trả về mỗi trang (tối đa {MAX_PAGE_SIZE})",
        ),
    ] = DEFAULT_PAGE_SIZE,
    doc_status: Annotated[
        DocumentStatus | None, Query(alias="status", description="Lọc theo trạng thái xử lý")
    ] = None,
    doc_type: Annotated[DocumentType | None, Query(description="Lọc theo loại văn bản")] = None,
    search: Annotated[
        str | None, Query(max_length=200, description="Tìm kiếm full-text theo tiêu đề và nội dung")
    ] = None,
) -> PaginatedResponse[DocumentResponse]:
    documents, total = await service.list_documents(
        offset=offset,
        limit=limit,
        status=doc_status,
        doc_type=doc_type,
        search=search,
    )

    return PaginatedResponse(
        data=[DocumentResponse.model_validate(d) for d in documents],
        meta=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_next=offset + limit < total,
            has_prev=offset > 0,
        ),
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Chi tiết tài liệu theo ID",
    description=(
        "Lấy toàn bộ thông tin của một tài liệu. Trả về 404 nếu không tìm thấy hoặc đã xoá."
    ),
)
async def get_document(
    document_id: UUID,
    service: DocumentServiceDep,
) -> DocumentResponse:
    document = await service.get_document(document_id)
    return DocumentResponse.model_validate(document)


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Cập nhật metadata tài liệu",
    description=(
        "Cập nhật một phần metadata (tiêu đề, số hiệu, ngày tháng, trạng thái...)."
        " Chỉ các field có giá trị mới được cập nhật."
    ),
)
async def update_document(
    document_id: UUID,
    body: DocumentUpdateRequest,
    service: DocumentServiceDep,
) -> DocumentResponse:
    dto = UpdateDocumentDTO(
        title=body.title,
        doc_number=body.doc_number,
        doc_type=body.doc_type,
        authority_level=body.authority_level,
        issuing_body=body.issuing_body,
        issued_date=body.issued_date,
        effective_date=body.effective_date,
        expired_date=body.expired_date,
        status=body.status,
        tags=body.tags,
        metadata_extra=body.metadata_extra,
    )
    document = await service.update_document(document_id, dto)
    return DocumentResponse.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá tài liệu (soft delete)",
    description=(
        "Đánh dấu tài liệu là đã xoá (điền deleted_at)."
        " Dữ liệu vật lý vẫn còn trong database và storage."
    ),
)
async def delete_document(
    document_id: UUID,
    service: DocumentServiceDep,
) -> None:
    await service.delete_document(document_id)
