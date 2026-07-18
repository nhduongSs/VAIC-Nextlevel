from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.application.commands.ingest_document import IngestionPipelineService
from app.application.services.document_service import DocumentService
from app.domain.repositories.chunk_repo import ChunkRepository
from app.domain.repositories.processing_log_repo import ProcessingLogRepository
from app.domain.repositories.relation_repo import DocumentRelationRepository
from app.presentation.exceptions import NotFoundException
from app.presentation.schemas.common_schema import PaginatedResponse, PaginationMeta
from app.presentation.schemas.ingestion_schema import (
    ChunkResponse,
    DocumentRelationResponse,
    ProcessingStatusResponse,
    TriggerProcessingResponse,
)
from app.utils.constants import API_V1_PREFIX, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix=f"{API_V1_PREFIX}/documents", tags=["Ingestion"])


# ── Dependency stubs (overridden in main.py) ─────────────────────────────────


def _get_ingestion_service() -> IngestionPipelineService:  # pragma: no cover
    raise NotImplementedError


def _get_document_service() -> DocumentService:  # pragma: no cover
    raise NotImplementedError


def _get_chunk_repo() -> ChunkRepository:  # pragma: no cover
    raise NotImplementedError


def _get_relation_repo() -> DocumentRelationRepository:  # pragma: no cover
    raise NotImplementedError


def _get_processing_log_repo() -> ProcessingLogRepository:  # pragma: no cover
    raise NotImplementedError


IngestionServiceDep = Annotated[IngestionPipelineService, Depends(_get_ingestion_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(_get_document_service)]
ChunkRepoDep = Annotated[ChunkRepository, Depends(_get_chunk_repo)]
RelationRepoDep = Annotated[DocumentRelationRepository, Depends(_get_relation_repo)]
LogRepoDep = Annotated[ProcessingLogRepository, Depends(_get_processing_log_repo)]


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post(
    "/{document_id}/process",
    response_model=TriggerProcessingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Kích hoạt pipeline ingestion tài liệu",
    description=(
        "Chạy pipeline xử lý tài liệu gồm 3 giai đoạn: "
        "**extract** (trích xuất text từ PDF/DOCX), "
        "**chunk** (chia văn bản thành các đoạn nhỏ), "
        "**detect_relations** (nhận diện quan hệ giữa văn bản). "
        "Pipeline chạy bất đồng bộ ở background — dùng `/processing-status` để theo dõi tiến độ."
    ),
)
async def trigger_processing(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    doc_service: DocumentServiceDep,
    ingestion_service: IngestionServiceDep,
) -> TriggerProcessingResponse:
    # Verify document exists and is not deleted
    document = await doc_service.get_document(document_id)

    background_tasks.add_task(ingestion_service.process, document.id)

    return TriggerProcessingResponse(
        document_id=document_id,
        message="Processing started",
    )


@router.get(
    "/{document_id}/processing-status",
    response_model=ProcessingStatusResponse,
    summary="Trạng thái pipeline ingestion mới nhất",
    description="Lấy log xử lý gần nhất của tài liệu. Trả về 404 nếu tài liệu chưa được gửi vào pipeline lần nào.",
)
async def get_processing_status(
    document_id: UUID,
    doc_service: DocumentServiceDep,
    log_repo: LogRepoDep,
) -> ProcessingStatusResponse:
    await doc_service.get_document(document_id)  # raises 404 if missing/deleted

    log = await log_repo.get_latest_by_document(document_id)
    if log is None:
        raise NotFoundException(f"No processing log found for document '{document_id}'")

    return ProcessingStatusResponse.model_validate(log)


@router.get(
    "/{document_id}/chunks",
    response_model=PaginatedResponse[ChunkResponse],
    summary="Danh sách chunks của tài liệu (có phân trang)",
    description="Lấy danh sách các chunk văn bản đã được tách từ tài liệu. Cần chạy pipeline ingestion trước.",
)
async def list_chunks(
    document_id: UUID,
    doc_service: DocumentServiceDep,
    chunk_repo: ChunkRepoDep,
    offset: Annotated[int, Query(ge=0, description="Số chunk bỏ qua (dùng cho phân trang)")] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description=f"Số chunk trả về mỗi trang (tối đa {MAX_PAGE_SIZE})")] = DEFAULT_PAGE_SIZE,
) -> PaginatedResponse[ChunkResponse]:
    await doc_service.get_document(document_id)

    total = await chunk_repo.count_by_document(document_id)
    page_chunks = await chunk_repo.get_by_document(document_id, offset=offset, limit=limit)

    return PaginatedResponse(
        data=[ChunkResponse.model_validate(c) for c in page_chunks],
        meta=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_next=offset + limit < total,
            has_prev=offset > 0,
        ),
    )


@router.get(
    "/{document_id}/relationships",
    response_model=list[DocumentRelationResponse],
    summary="Danh sách quan hệ pháp lý của tài liệu",
    description=(
        "Lấy các quan hệ được nhận diện giữa tài liệu này và các văn bản khác "
        "(ví dụ: sửa đổi, thay thế, hướng dẫn thi hành). "
        "Kết quả bao gồm cả quan hệ đi ra (source) lẫn đi vào (target)."
    ),
)
async def list_relationships(
    document_id: UUID,
    doc_service: DocumentServiceDep,
    relation_repo: RelationRepoDep,
) -> list[DocumentRelationResponse]:
    await doc_service.get_document(document_id)

    relations = await relation_repo.get_by_document(document_id)
    return [DocumentRelationResponse.model_validate(r) for r in relations]
