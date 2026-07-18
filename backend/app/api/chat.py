"""Chat endpoint — new endpoint added in flat restructure."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_chat_service
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse, summary="Chat với trợ lý pháp lý NHNN")
async def chat(
    body: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """
    Gửi câu hỏi, nhận câu trả lời có trích dẫn nguồn văn bản pháp lý.

    Pipeline:
    1. Guardrail kiểm tra đầu vào
    2. Hybrid retrieval (BM25 + vector)
    3. Knowledge Intelligence (version resolution, conflict detection)
    4. LLM tổng hợp câu trả lời
    5. Guardrail kiểm tra đầu ra
    """
    return await service.handle_message(body.session_id, body.message)
