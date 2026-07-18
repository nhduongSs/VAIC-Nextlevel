"""Embedding endpoints — from presentation/routers/embedding_router.py."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.core.dependencies import get_embedding_service
from app.models.schemas import EmbeddingJobResponse, EmbeddingStatusResponse
from app.services.embedding_service import EmbeddingService
from app.utils.constants import API_V1_PREFIX

router = APIRouter(
    prefix=f"{API_V1_PREFIX}/documents/{{document_id}}/embeddings",
    tags=["Embeddings"],
)

EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]


@router.post(
    "",
    response_model=EmbeddingStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Kích hoạt tạo vector embedding cho tài liệu",
)
async def trigger_embedding(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    svc: EmbeddingServiceDep,
) -> EmbeddingStatusResponse:
    background_tasks.add_task(svc.embed_document, document_id)
    return EmbeddingStatusResponse(
        document_id=document_id,
        job_id=None,
        status=None,
        progress_pct=0.0,
        embedded_chunks=0,
        total_chunks=0,
        model_name=None,
    )


@router.get(
    "/status",
    response_model=EmbeddingStatusResponse,
    summary="Trạng thái embedding job mới nhất",
)
async def get_embedding_status(
    document_id: UUID,
    svc: EmbeddingServiceDep,
) -> EmbeddingStatusResponse:
    job = await svc.get_job_status(document_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No embedding job found for this document",
        )
    return EmbeddingStatusResponse(
        document_id=document_id,
        job_id=job.id,
        status=job.status,
        progress_pct=job.progress_pct,
        embedded_chunks=job.embedded_chunks,
        total_chunks=job.total_chunks,
        model_name=job.model_name,
    )


@router.get(
    "",
    response_model=list[EmbeddingJobResponse],
    summary="Lịch sử tất cả embedding jobs của tài liệu",
)
async def list_embedding_jobs(
    document_id: UUID,
    svc: EmbeddingServiceDep,
) -> list[EmbeddingJobResponse]:
    jobs = await svc.list_jobs(document_id)
    return [
        EmbeddingJobResponse(
            id=j.id,
            document_id=j.document_id,
            status=j.status,
            model_name=j.model_name,
            total_chunks=j.total_chunks,
            embedded_chunks=j.embedded_chunks,
            failed_chunks=j.failed_chunks,
            retry_count=j.retry_count,
            progress_pct=j.progress_pct,
            started_at=j.started_at,
            completed_at=j.completed_at,
            error_message=j.error_message,
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Huỷ embedding job đang chạy",
)
async def cancel_embedding_job(
    document_id: UUID,
    job_id: UUID,
    svc: EmbeddingServiceDep,
) -> None:
    cancelled = await svc.cancel_job(job_id, document_id=document_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or already in terminal state",
        )
