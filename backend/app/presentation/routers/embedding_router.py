from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.application.services.embedding_service import EmbeddingService
from app.presentation.schemas.embedding_schema import EmbeddingJobResponse, EmbeddingStatusResponse
from app.utils.constants import API_V1_PREFIX

router = APIRouter(
    prefix=f"{API_V1_PREFIX}/documents/{{document_id}}/embeddings",
    tags=["Embeddings"],
)


# ── Dependency stub (overridden in main.py) ───────────────────────────────────


def _get_embedding_service() -> EmbeddingService:  # pragma: no cover
    raise NotImplementedError


EmbeddingServiceDep = Annotated[EmbeddingService, Depends(_get_embedding_service)]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=EmbeddingStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Kích hoạt tạo vector embedding cho tài liệu",
    description=(
        "Chạy embedding pipeline bất đồng bộ: lấy tất cả chunk của tài liệu, "
        "gửi theo batch tới embedding service (BGE-M3, 1024 chiều), "
        "lưu vector vào cột `chunks.embedding`. "
        "Dùng `/embeddings/status` để theo dõi tiến độ. "
        "Tài liệu cần được chạy ingestion pipeline trước để có chunk."
    ),
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
    description=(
        "Lấy trạng thái và tiến độ của embedding job gần nhất. Trả về 404 nếu chưa có job nào."
    ),
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
    description=(
        "Lấy toàn bộ lịch sử embedding jobs theo thứ tự mới nhất trước."
        " Hữu ích để kiểm tra các lần retry."
    ),
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
    description=(
        "Huỷ một embedding job ở trạng thái PENDING hoặc RUNNING. "
        "Trả về 404 nếu job không tồn tại, không thuộc tài liệu này,"
        " hoặc đã ở trạng thái terminal (COMPLETED/FAILED/CANCELLED)."
    ),
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
