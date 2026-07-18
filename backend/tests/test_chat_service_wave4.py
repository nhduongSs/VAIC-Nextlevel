"""Tests for the Wave 4 ChatService — all dependencies are mocked."""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.generation.llm.deepseek_service import GenerationResult
from app.generation.prompt.config import PromptConfig, PromptType
from app.generation.prompt.package import PromptPackage
from app.generation.response.package import AnswerPackage, UsageStatistics
from app.models.enums import SearchResult
from app.models.schemas import ChatResponse
from app.services.chat_service import ChatService
from app.services.document_relation_service import ContextPackage
from app.services.guardrail_service import GuardrailResult


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _make_guardrail_service(
    input_allowed: bool = True,
    retrieval_allowed: bool = True,
) -> MagicMock:
    svc = MagicMock()
    svc.check_input.return_value = GuardrailResult(
        allowed=input_allowed,
        reason="none" if input_allowed else "unsafe_request",
        message="" if input_allowed else "Blocked input",
    )
    svc.check_retrieval.return_value = GuardrailResult(
        allowed=retrieval_allowed,
        reason="none" if retrieval_allowed else "out_of_scope",
        message="" if retrieval_allowed else "No results",
    )
    svc.check_output.side_effect = lambda x: x  # pass-through
    return svc


def _empty_context_package() -> ContextPackage:
    return ContextPackage(
        query="test",
        ranked_chunks=[],
        citations=[],
        relationships=[],
        conflicts=[],
        timeline=[],
        metadata={},
        statistics={},
    )


def _context_package_with_chunk() -> ContextPackage:
    chunk = SearchResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="Content",
        score=0.9,
        retrieval_method="hybrid",
        bm25_score=None,
        vector_score=None,
        chunk_index=0,
        chunk_type="text",
        section_title="Điều 1",
        section_number="1",
        page_number=1,
        bank="BIDV",
        category="lai_suat",
        metadata={},
    )
    return ContextPackage(
        query="test",
        ranked_chunks=[chunk],
        citations=[],
        relationships=[],
        conflicts=[],
        timeline=[],
        metadata={},
        statistics={},
    )


def _make_prompt_package() -> PromptPackage:
    return PromptPackage(
        prompt_type=PromptType.QA,
        system_prompt="System",
        user_prompt="User",
        estimated_prompt_tokens=100,
        estimated_completion_tokens=2048,
        estimated_total_tokens=2148,
        context_chunks_used=1,
        citations_used=0,
        was_truncated=False,
        config=PromptConfig(),
    )


def _make_generation_result() -> GenerationResult:
    return GenerationResult(
        content="Đây là câu trả lời.",
        prompt_tokens=100,
        completion_tokens=40,
        total_tokens=140,
        retry_count=0,
        latency_ms=200.0,
        provider="deepseek",
        model="deepseek-chat",
    )


def _make_answer_package(session_id: str = "sess-001") -> AnswerPackage:
    return AnswerPackage(
        session_id=session_id,
        question="Lãi suất?",
        answer="Đây là câu trả lời.",
        sources=[],
        conflicts=[],
        timeline=[],
        usage=UsageStatistics.from_tokens(
            prompt_tokens=100,
            completion_tokens=40,
            retry_count=0,
            provider="deepseek",
            model="deepseek-chat",
        ),
        prompt_type=PromptType.QA,
        confidence_score=0.9,
        latency_ms=300.0,
        provider="deepseek",
        model="deepseek-chat",
    )


def _make_chat_service(
    guardrail: MagicMock,
    rag_chunks: list | None = None,
    context_package: ContextPackage | None = None,
    prompt_package: PromptPackage | None = None,
    generation_result: GenerationResult | None = None,
    answer_package: AnswerPackage | None = None,
) -> ChatService:
    """Build a ChatService with fully mocked sub-components."""
    rag = MagicMock()
    rag.retrieve = AsyncMock(return_value=rag_chunks or [])

    relations = MagicMock()
    relations.process = AsyncMock(
        return_value=context_package or _empty_context_package()
    )

    prompt_builder = MagicMock()
    prompt_builder.build.return_value = prompt_package or _make_prompt_package()

    deepseek_service = MagicMock()
    deepseek_service.generate = AsyncMock(
        return_value=generation_result or _make_generation_result()
    )
    deepseek_service.health_check = AsyncMock(return_value=True)

    response_formatter = MagicMock()
    pkg = answer_package or _make_answer_package()
    response_formatter.format.return_value = pkg
    response_formatter.to_chat_response.return_value = ChatResponse(
        session_id=pkg.session_id,
        answer=pkg.answer,
        sources=pkg.sources,
        conflicts=pkg.conflicts,
        blocked=pkg.blocked,
        block_reason=pkg.block_reason,
    )

    return ChatService(
        rag=rag,
        relations=relations,
        guardrail=guardrail,
        prompt_builder=prompt_builder,
        deepseek_service=deepseek_service,
        response_formatter=response_formatter,
    )


# ---------------------------------------------------------------------------
# Tests: handle_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_message_blocked_by_input_guardrail() -> None:
    guardrail = _make_guardrail_service(input_allowed=False)
    service = _make_chat_service(guardrail=guardrail)

    response = await service.handle_message("sess-1", "Inject prompt")

    assert response.blocked is True
    assert response.block_reason == "unsafe_request"
    # RAG should never be called if guardrail blocks
    service.rag.retrieve.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_handle_message_blocked_by_retrieval_guardrail() -> None:
    """When retrieval returns nothing, retrieval guardrail should block."""
    guardrail = _make_guardrail_service(input_allowed=True, retrieval_allowed=False)
    service = _make_chat_service(
        guardrail=guardrail,
        context_package=_empty_context_package(),  # no chunks
    )

    response = await service.handle_message("sess-2", "Lãi suất?")

    assert response.blocked is True
    assert response.block_reason == "out_of_scope"


@pytest.mark.asyncio
async def test_handle_message_succeeds_with_full_pipeline() -> None:
    guardrail = _make_guardrail_service(input_allowed=True, retrieval_allowed=True)
    context_pkg = _context_package_with_chunk()
    service = _make_chat_service(
        guardrail=guardrail,
        context_package=context_pkg,
    )

    response = await service.handle_message("sess-3", "Lãi suất tiết kiệm?")

    assert response.blocked is False
    assert response.answer == "Đây là câu trả lời."
    assert response.session_id == "sess-001"  # from _make_answer_package default
    # DeepSeekService.generate should be called once
    service.deepseek_service.generate.assert_called_once()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_handle_message_empty_retrieval_blocked() -> None:
    """Empty context_package.ranked_chunks causes retrieval guardrail to fire."""
    guardrail = _make_guardrail_service(input_allowed=True, retrieval_allowed=False)
    # rag returns no chunks; retrieval guardrail triggers
    service = _make_chat_service(
        guardrail=guardrail,
        rag_chunks=[],
    )

    response = await service.handle_message("sess-4", "Câu hỏi không liên quan")

    assert response.blocked is True


# ---------------------------------------------------------------------------
# Tests: stream_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_message_yields_sse_tokens() -> None:
    guardrail = _make_guardrail_service(input_allowed=True, retrieval_allowed=True)
    context_pkg = _context_package_with_chunk()

    tokens = ["Đây ", "là ", "câu ", "trả ", "lời."]

    async def _mock_stream(pkg: PromptPackage) -> AsyncGenerator[str, None]:
        for t in tokens:
            yield t

    rag = MagicMock()
    rag.retrieve = AsyncMock(return_value=[])

    relations = MagicMock()
    relations.process = AsyncMock(return_value=context_pkg)

    prompt_builder = MagicMock()
    prompt_builder.build.return_value = _make_prompt_package()

    deepseek_service = MagicMock()
    deepseek_service.stream_generate = _mock_stream  # type: ignore[assignment]
    deepseek_service.health_check = AsyncMock(return_value=True)

    response_formatter = MagicMock()

    service = ChatService(
        rag=rag,
        relations=relations,
        guardrail=guardrail,
        prompt_builder=prompt_builder,
        deepseek_service=deepseek_service,
        response_formatter=response_formatter,
    )

    collected: list[str] = []
    async for chunk in service.stream_message("sess-5", "Lãi suất?"):
        collected.append(chunk)

    # Each token should be wrapped as SSE event
    assert any("Đây " in c for c in collected)
    # Final event should be [DONE]
    assert collected[-1] == "data: [DONE]\n\n"


@pytest.mark.asyncio
async def test_stream_message_blocked_by_input_guardrail() -> None:
    guardrail = _make_guardrail_service(input_allowed=False)
    service = _make_chat_service(guardrail=guardrail)

    collected: list[str] = []
    async for chunk in service.stream_message("sess-6", "bad input"):
        collected.append(chunk)

    # Should immediately yield the blocked message and [DONE]
    assert len(collected) == 2
    assert "[DONE]" in collected[-1]


# ---------------------------------------------------------------------------
# Tests: health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_returns_ok_when_llm_healthy() -> None:
    guardrail = _make_guardrail_service()
    service = _make_chat_service(guardrail=guardrail)
    # deepseek_service.health_check already returns True in helper

    result = await service.health()

    assert result["status"] == "ok"
    assert result["llm"] is True
    assert result["provider"] == "deepseek"
