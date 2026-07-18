"""Chat endpoints — POST /chat, POST /chat/stream, GET /chat/health."""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

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
    4. Prompt building (PromptBuilder)
    5. LLM generation (DeepSeekService)
    6. Response formatting (ResponseFormatter)
    7. Guardrail kiểm tra đầu ra
    """
    return await service.handle_message(body.session_id, body.message)


@router.post(
    "/stream",
    summary="Stream câu trả lời qua SSE",
    response_class=StreamingResponse,
)
async def chat_stream(
    body: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """
    Stream câu trả lời theo định dạng SSE (Server-Sent Events).

    Mỗi sự kiện có dạng:
    ```
    data: {token}\\n\\n
    ```

    Khi hoàn thành:
    ```
    data: [DONE]\\n\\n
    ```
    """

    async def _event_generator() -> AsyncGenerator[str, None]:
        async for chunk in service.stream_message(body.session_id, body.message):
            yield chunk

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/health",
    summary="Kiểm tra trạng thái pipeline chat",
)
async def chat_health(
    service: ChatService = Depends(get_chat_service),
) -> dict[str, object]:
    """
    Kiểm tra kết nối LLM và trạng thái pipeline.

    Trả về:
    - ``status``: ``"ok"`` hoặc ``"degraded"``
    - ``llm``: trạng thái kết nối DeepSeek
    - ``provider``: tên provider đang dùng
    """
    return await service.health()
