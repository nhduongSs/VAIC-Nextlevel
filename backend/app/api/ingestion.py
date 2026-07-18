"""Ingestion endpoints — from presentation/routers/ingestion_router.py."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.core.dependencies import (
    get_chunk_repository,
    get_document_service,
    get_ingestion_pipeline_service,
    get_processing_log_repository,
    get_relation_repository,
)
from app.core.exceptions import NotFoundException
from app.models.schemas import (
    ChunkResponse,
    DocumentRelationResponse,
    PaginatedResponse,
    PaginationMeta,
    ProcessingStatusResponse,
    TriggerProcessingResponse,
)
from app.repositories.document_store import PgChunkRepository, PgProcessingLogRepository
from app.repositories.relation_store import PgDocumentRelationRepository
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionPipelineService
from app.utils.constants import API_V1_PREFIX, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix=f"{API_V1_PREFIX}/documents", tags=["Ingestion"])

IngestionServiceDep = Annotated[
    IngestionPipelineService, Depends(get_ingestion_pipeline_service)
]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
ChunkRepoDep = Annotated[PgChunkRepository, Depends(get_chunk_repository)]
RelationRepoDep = Annotated[
    PgDocumentRelationRepository, Depends(get_relation_repository)
]
LogRepoDep = Annotated[
    PgProcessingLogRepository, Depends(get_processing_log_repository)
]


@router.post(
    "/{document_id}/process",
    response_model=TriggerProcessingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Kích hoạt pipeline ingestion tài liệu",
)
async def trigger_processing(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    doc_service: DocumentServiceDep,
    ingestion_service: IngestionServiceDep,
) -> TriggerProcessingResponse:
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
)
async def get_processing_status(
    document_id: UUID,
    doc_service: DocumentServiceDep,
    log_repo: LogRepoDep,
) -> ProcessingStatusResponse:
    await doc_service.get_document(document_id)
    log = await log_repo.get_latest_by_document(document_id)
    if log is None:
        raise NotFoundException(f"No processing log found for document '{document_id}'")
    return ProcessingStatusResponse.model_validate(log)


@router.get(
    "/{document_id}/chunks",
    response_model=PaginatedResponse[ChunkResponse],
    summary="Danh sách chunks của tài liệu (có phân trang)",
)
async def list_chunks(
    document_id: UUID,
    doc_service: DocumentServiceDep,
    chunk_repo: ChunkRepoDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PaginatedResponse[ChunkResponse]:
    await doc_service.get_document(document_id)
    total = await chunk_repo.count_by_document(document_id)
    page_chunks = await chunk_repo.get_by_document(
        document_id, offset=offset, limit=limit
    )
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
)
async def list_relationships(
    document_id: UUID,
    doc_service: DocumentServiceDep,
    relation_repo: RelationRepoDep,
) -> list[DocumentRelationResponse]:
    await doc_service.get_document(document_id)
    relations = await relation_repo.get_by_document(document_id)
    return [DocumentRelationResponse.model_validate(r) for r in relations]
