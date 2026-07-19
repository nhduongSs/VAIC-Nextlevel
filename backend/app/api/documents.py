"""Document CRUD endpoints — from presentation/routers/document_router.py."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.core.dependencies import get_document_service, require_permission
from app.models.enums import AuthorityLevel, DocumentStatus, DocumentType
from app.models.orm import UserModel
from app.models.schemas import (
    DocumentResponse,
    DocumentUpdateRequest,
    PaginatedResponse,
    PaginationMeta,
)
from app.services.document_service import DocumentService
from app.utils.constants import API_V1_PREFIX, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix=f"{API_V1_PREFIX}/documents", tags=["Documents"])

DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


# ── DTOs (inline to avoid importing old application/dto) ─────────────────────


@dataclass
class _CreateDTO:
    title: str
    doc_type: DocumentType
    authority_level: AuthorityLevel
    doc_number: str | None = None
    issuing_body: str | None = None
    issued_date: date | None = None
    effective_date: date | None = None
    expired_date: date | None = None
    tags: list[str] | None = None
    metadata_extra: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []


@dataclass
class _UpdateDTO:
    title: str | None = None
    doc_number: str | None = None
    doc_type: DocumentType | None = None
    authority_level: AuthorityLevel | None = None
    issuing_body: str | None = None
    issued_date: date | None = None
    effective_date: date | None = None
    expired_date: date | None = None
    status: DocumentStatus | None = None
    tags: list[str] | None = None
    metadata_extra: dict[str, Any] | None = None


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload tài liệu mới",
    description=(
        "Upload file PDF/DOCX/TXT kèm metadata văn bản pháp lý. "
        "File được lưu vào storage, hash nội dung được tính để phát hiện trùng lặp. "
        "Trả về thông tin tài liệu vừa tạo với trạng thái UPLOADED."
    ),
)
async def upload_document(
    service: DocumentServiceDep,
    file: Annotated[
        UploadFile, File(description="File tài liệu cần upload (PDF, DOCX, TXT)")
    ],
    title: Annotated[
        str, Form(min_length=1, max_length=500, description="Tiêu đề văn bản")
    ],
    doc_type: Annotated[DocumentType, Form(description="Loại văn bản")],
    authority_level: Annotated[AuthorityLevel, Form(description="Cấp thẩm quyền")],
    doc_number: Annotated[str | None, Form(max_length=100)] = None,
    issuing_body: Annotated[str | None, Form(max_length=200)] = None,
    issued_date: Annotated[date | None, Form()] = None,
    effective_date: Annotated[date | None, Form()] = None,
    expired_date: Annotated[date | None, Form()] = None,
) -> DocumentResponse:
    dto = _CreateDTO(
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
)
async def list_documents(
    service: DocumentServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    doc_status: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    doc_type: Annotated[DocumentType | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
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
    "/{document_id}", response_model=DocumentResponse, summary="Chi tiết tài liệu"
)
async def get_document(
    document_id: UUID,
    service: DocumentServiceDep,
) -> DocumentResponse:
    document = await service.get_document(document_id)
    return DocumentResponse.model_validate(document)


@router.patch(
    "/{document_id}", response_model=DocumentResponse, summary="Cập nhật metadata"
)
async def update_document(
    document_id: UUID,
    body: DocumentUpdateRequest,
    service: DocumentServiceDep,
) -> DocumentResponse:
    dto = _UpdateDTO(
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
    summary="Xoá tài liệu (soft delete) — yêu cầu quyền documents:delete",
)
async def delete_document(
    document_id: UUID,
    service: DocumentServiceDep,
    _: Annotated[UserModel, Depends(require_permission("documents:delete"))],
) -> None:
    await service.delete_document(document_id)
