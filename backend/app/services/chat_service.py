"""ChatService — orchestrates the full RAG + Generation pipeline (Wave 4)."""
from __future__ import annotations

import time
from collections.abc import AsyncGenerator

import structlog

from app.generation.llm.deepseek_service import DeepSeekService
from app.generation.prompt.builder import PromptBuilder
from app.generation.prompt.config import PromptType
from app.generation.response.formatter import ResponseFormatter
from app.models.schemas import ChatResponse
from app.services.document_relation_service import DocumentRelationService
from app.services.guardrail_service import GuardrailService
from app.services.rag_service import RAGService

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class ChatService:
    """Full RAG → Generation pipeline service.

    Steps in :meth:`handle_message`:
    1. Input guardrail
    2. Small talk short-circuit (greetings/thanks/etc — no RAG, no citations)
    3. Hybrid retrieval (RAGService)
    4. Knowledge Intelligence pipeline (DocumentRelationService)
    5. Retrieval guardrail
    6. Prompt building (PromptBuilder)
    7. LLM generation (DeepSeekService)
    8. Response formatting (ResponseFormatter)
    9. Output guardrail
    """

    def __init__(
        self,
        rag: RAGService,
        relations: DocumentRelationService,
        guardrail: GuardrailService,
        prompt_builder: PromptBuilder,
        deepseek_service: DeepSeekService,
        response_formatter: ResponseFormatter,
    ) -> None:
        self.rag = rag
        self.relations = relations
        self.guardrail = guardrail
        self.prompt_builder = prompt_builder
        self.deepseek_service = deepseek_service
        self.response_formatter = response_formatter

    async def handle_message(self, session_id: str, message: str) -> ChatResponse:
        """Process a user message through the full pipeline."""
        t0 = time.perf_counter()

        # ── 1. Input guardrail ─────────────────────────────────────────────
        input_check = self.guardrail.check_input(message)
        if not input_check.allowed:
            log.info(
                "chat_input_blocked",
                session_id=session_id,
                reason=input_check.reason,
            )
            return ChatResponse(
                session_id=session_id,
                answer=input_check.message,
                blocked=True,
                block_reason=input_check.reason,
            )

        # ── 2. Small talk short-circuit ─────────────────────────────────────
        small_talk_reply = self.guardrail.check_small_talk(message)
        if small_talk_reply is not None:
            log.info("chat_small_talk", session_id=session_id)
            return ChatResponse(session_id=session_id, answer=small_talk_reply)

        # ── 3. Hybrid retrieval ────────────────────────────────────────────
        chunks = await self.rag.retrieve(message)

        # ── 4. Knowledge Intelligence pipeline ────────────────────────────
        context_package = await self.relations.process(message, chunks)

        # ── 5. Retrieval guardrail ─────────────────────────────────────────
        retrieval_check = self.guardrail.check_retrieval(context_package.ranked_chunks)
        if not retrieval_check.allowed:
            log.info(
                "chat_retrieval_blocked",
                session_id=session_id,
                reason=retrieval_check.reason,
            )
            return ChatResponse(
                session_id=session_id,
                answer=retrieval_check.message,
                blocked=True,
                block_reason=retrieval_check.reason,
            )

        # ── 6. Build prompt ────────────────────────────────────────────────
        prompt_package = self.prompt_builder.build(
            context_package=context_package,
            prompt_type=PromptType.QA,
        )

        # ── 7. Generate ────────────────────────────────────────────────────
        generation_result = await self.deepseek_service.generate(prompt_package)

        # ── 8. Output guardrail ────────────────────────────────────────────
        generation_result.content = self.guardrail.check_output(
            generation_result.content
        )

        # ── 9. Format response ─────────────────────────────────────────────
        total_latency_ms = (time.perf_counter() - t0) * 1000
        answer_package = self.response_formatter.format(
            session_id=session_id,
            question=message,
            generation_result=generation_result,
            context_package=context_package,
            prompt_package=prompt_package,
            total_latency_ms=total_latency_ms,
        )

        log.info(
            "chat_handle_message_done",
            session_id=session_id,
            latency_ms=round(total_latency_ms, 1),
            chunks=len(context_package.ranked_chunks),
            citations=len(context_package.citations),
        )

        return self.response_formatter.to_chat_response(answer_package)

    async def stream_message(
        self, session_id: str, message: str
    ) -> AsyncGenerator[str, None]:
        """Stream answer tokens as SSE chunks.

        Yields strings formatted as SSE events:
        ``data: {chunk_text}\\n\\n``

        On completion yields ``data: [DONE]\\n\\n``.
        """
        # ── 1. Input guardrail ─────────────────────────────────────────────
        input_check = self.guardrail.check_input(message)
        if not input_check.allowed:
            yield f"data: {input_check.message}\n\n"
            yield "data: [DONE]\n\n"
            return

        # ── 2. Small talk short-circuit ─────────────────────────────────────
        small_talk_reply = self.guardrail.check_small_talk(message)
        if small_talk_reply is not None:
            yield f"data: {small_talk_reply}\n\n"
            yield "data: [DONE]\n\n"
            return

        # ── 3. Retrieval ───────────────────────────────────────────────────
        chunks = await self.rag.retrieve(message)
        context_package = await self.relations.process(message, chunks)

        # ── 4. Retrieval guardrail ─────────────────────────────────────────
        retrieval_check = self.guardrail.check_retrieval(context_package.ranked_chunks)
        if not retrieval_check.allowed:
            yield f"data: {retrieval_check.message}\n\n"
            yield "data: [DONE]\n\n"
            return

        # ── 5. Build prompt ────────────────────────────────────────────────
        prompt_package = self.prompt_builder.build(
            context_package=context_package,
            prompt_type=PromptType.QA,
        )

        # ── 6. Stream generation ───────────────────────────────────────────
        log.info("chat_stream_start", session_id=session_id)
        async for token in self.deepseek_service.stream_generate(prompt_package):
            yield f"data: {token}\n\n"

        yield "data: [DONE]\n\n"

    async def health(self) -> dict[str, object]:
        """Return a health-status dictionary for the chat pipeline."""
        llm_ok = await self.deepseek_service.health_check()
        return {
            "status": "ok" if llm_ok else "degraded",
            "llm": llm_ok,
            "provider": "deepseek",
        }
