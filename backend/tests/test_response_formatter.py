"""Tests for ResponseFormatter, CitationFormatter, and UsageStatistics."""
from __future__ import annotations

import uuid
from datetime import date


from app.generation.llm.deepseek_service import GenerationResult
from app.generation.prompt.config import PromptConfig, PromptType
from app.generation.prompt.package import PromptPackage
from app.generation.response.citation_formatter import CitationFormatter
from app.generation.response.formatter import ResponseFormatter
from app.generation.response.package import AnswerPackage, UsageStatistics
from app.models.enums import SearchResult
from app.services.document_relation_service import (
    Citation,
    ConflictInfo,
    ContextPackage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_citation(chunk_id: uuid.UUID | None = None) -> Citation:
    cid = chunk_id or uuid.uuid4()
    return Citation(
        chunk_id=cid,
        document_id=uuid.uuid4(),
        document_title="Thông tư 01/2024",
        doc_number="01/2024/TT-NHNN",
        section_title="Điều 1. Phạm vi áp dụng",
        section_number="Điều 1",
        page_number=2,
        chunk_index=0,
        authority_level="NHNN_CIRCULAR",
        version=1,
        effective_date=date(2024, 1, 1),
        content_preview="Thông tư này quy định về lãi suất...",
    )


def _make_chunk(chunk_id: uuid.UUID, score: float = 0.85) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=uuid.uuid4(),
        content="Nội dung điều khoản...",
        score=score,
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


def _make_generation_result(content: str = "Câu trả lời.") -> GenerationResult:
    return GenerationResult(
        content=content,
        prompt_tokens=200,
        completion_tokens=80,
        total_tokens=280,
        retry_count=0,
        latency_ms=345.0,
        provider="deepseek",
        model="deepseek-chat",
    )


def _make_prompt_package() -> PromptPackage:
    return PromptPackage(
        prompt_type=PromptType.QA,
        system_prompt="System",
        user_prompt="User question",
        estimated_prompt_tokens=300,
        estimated_completion_tokens=2048,
        estimated_total_tokens=2348,
        context_chunks_used=2,
        citations_used=2,
        was_truncated=False,
        config=PromptConfig(),
    )


def _make_context_package(n_chunks: int = 2) -> ContextPackage:
    chunks = [_make_chunk(chunk_id=uuid.uuid4(), score=0.9 - i * 0.1) for i in range(n_chunks)]
    citations = [_make_citation(chunk_id=c.chunk_id) for c in chunks]
    return ContextPackage(
        query="Lãi suất là bao nhiêu?",
        ranked_chunks=chunks,
        citations=citations,
        relationships=[],
        conflicts=[],
        timeline=[],
        metadata={},
        statistics={},
    )


# ---------------------------------------------------------------------------
# UsageStatistics
# ---------------------------------------------------------------------------


class TestUsageStatistics:
    def test_cost_calculation(self) -> None:
        usage = UsageStatistics.from_tokens(
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            retry_count=0,
            provider="deepseek",
            model="deepseek-chat",
        )
        # $0.14 input + $0.28 output = $0.42 for 1M+1M tokens
        assert abs(usage.estimated_cost_usd - 0.42) < 1e-6

    def test_zero_tokens_zero_cost(self) -> None:
        usage = UsageStatistics.from_tokens(
            prompt_tokens=0,
            completion_tokens=0,
            retry_count=0,
            provider="deepseek",
            model="deepseek-chat",
        )
        assert usage.estimated_cost_usd == 0.0

    def test_total_tokens_summed(self) -> None:
        usage = UsageStatistics.from_tokens(
            prompt_tokens=100,
            completion_tokens=50,
            retry_count=0,
            provider="deepseek",
            model="deepseek-chat",
        )
        assert usage.total_tokens == 150

    def test_provider_and_model_stored(self) -> None:
        usage = UsageStatistics.from_tokens(
            prompt_tokens=0,
            completion_tokens=0,
            retry_count=1,
            provider="deepseek",
            model="deepseek-v3",
        )
        assert usage.provider == "deepseek"
        assert usage.model == "deepseek-v3"
        assert usage.retry_count == 1


# ---------------------------------------------------------------------------
# CitationFormatter
# ---------------------------------------------------------------------------


class TestCitationFormatter:
    def test_format_citation_contains_index(self) -> None:
        fmt = CitationFormatter()
        cit = _make_citation()
        result = fmt.format_citation(cit, index=3)
        assert result.startswith("[3]")

    def test_format_citation_contains_doc_number(self) -> None:
        fmt = CitationFormatter()
        cit = _make_citation()
        result = fmt.format_citation(cit, index=1)
        assert "01/2024/TT-NHNN" in result

    def test_format_citation_uses_unknown_when_no_doc_number(self) -> None:
        fmt = CitationFormatter()
        cit = _make_citation()
        cit.doc_number = None
        result = fmt.format_citation(cit, index=1)
        assert "Unknown" in result

    def test_format_citation_list_numbered(self) -> None:
        fmt = CitationFormatter()
        citations = [_make_citation(), _make_citation()]
        result = fmt.format_citation_list(citations)
        assert "[1]" in result
        assert "[2]" in result

    def test_format_citation_list_empty(self) -> None:
        fmt = CitationFormatter()
        assert fmt.format_citation_list([]) == ""

    def test_to_source_schema_populates_fields(self) -> None:
        fmt = CitationFormatter()
        cit = _make_citation()
        chunk = _make_chunk(chunk_id=cit.chunk_id)
        source = fmt.to_source_schema(cit, chunk)
        assert source.doc_id == str(cit.document_id)
        assert source.title == "Thông tư 01/2024"
        assert source.bank == "BIDV"
        assert source.effective_date == "2024-01-01"

    def test_to_source_schema_no_chunk(self) -> None:
        fmt = CitationFormatter()
        cit = _make_citation()
        source = fmt.to_source_schema(cit, chunk=None)
        assert source.bank is None


# ---------------------------------------------------------------------------
# ResponseFormatter
# ---------------------------------------------------------------------------


class TestResponseFormatter:
    def test_format_returns_answer_package(self) -> None:
        formatter = ResponseFormatter()
        ctx = _make_context_package(n_chunks=2)
        gen = _make_generation_result()
        prompt = _make_prompt_package()

        result = formatter.format(
            session_id="sess-001",
            question="Lãi suất?",
            generation_result=gen,
            context_package=ctx,
            prompt_package=prompt,
            total_latency_ms=500.0,
        )

        assert isinstance(result, AnswerPackage)
        assert result.session_id == "sess-001"
        assert result.answer == "Câu trả lời."
        assert len(result.sources) == 2
        assert result.confidence_score >= 0.0
        assert result.confidence_score <= 1.0

    def test_format_calculates_confidence_from_chunk_scores(self) -> None:
        formatter = ResponseFormatter()
        # Chunks with known scores
        chunk_ids = [uuid.uuid4() for _ in range(3)]
        chunks = [
            _make_chunk(chunk_id=chunk_ids[i], score=0.9 - i * 0.1)
            for i in range(3)
        ]
        citations = [_make_citation(chunk_id=c.chunk_id) for c in chunks]
        ctx = ContextPackage(
            query="test",
            ranked_chunks=chunks,
            citations=citations,
            relationships=[],
            conflicts=[],
            timeline=[],
            metadata={},
            statistics={},
        )
        result = formatter.format(
            session_id="s",
            question="q",
            generation_result=_make_generation_result(),
            context_package=ctx,
            prompt_package=_make_prompt_package(),
            total_latency_ms=100.0,
        )
        expected = (0.9 + 0.8 + 0.7) / 3
        assert abs(result.confidence_score - round(expected, 4)) < 1e-4

    def test_format_no_chunks_gives_zero_confidence(self) -> None:
        formatter = ResponseFormatter()
        ctx = ContextPackage(
            query="test",
            ranked_chunks=[],
            citations=[],
            relationships=[],
            conflicts=[],
            timeline=[],
            metadata={},
            statistics={},
        )
        result = formatter.format(
            session_id="s",
            question="q",
            generation_result=_make_generation_result(),
            context_package=ctx,
            prompt_package=_make_prompt_package(),
            total_latency_ms=100.0,
        )
        assert result.confidence_score == 0.0

    def test_to_chat_response_converts_correctly(self) -> None:
        formatter = ResponseFormatter()
        ctx = _make_context_package()
        gen = _make_generation_result()
        prompt = _make_prompt_package()
        answer_pkg = formatter.format(
            session_id="sess-xyz",
            question="Q",
            generation_result=gen,
            context_package=ctx,
            prompt_package=prompt,
            total_latency_ms=200.0,
        )
        chat_resp = formatter.to_chat_response(answer_pkg)
        assert chat_resp.session_id == "sess-xyz"
        assert chat_resp.answer == gen.content
        assert chat_resp.blocked is False
        assert chat_resp.block_reason == "none"

    def test_format_includes_conflicts(self) -> None:
        formatter = ResponseFormatter()
        conflict = ConflictInfo(
            source_doc_id=uuid.uuid4(),
            target_doc_id=uuid.uuid4(),
            source_title="TT 01",
            target_title="TT 02",
            description="Mâu thuẫn lãi suất",
            confidence=0.9,
        )
        ctx = ContextPackage(
            query="test",
            ranked_chunks=[],
            citations=[],
            relationships=[],
            conflicts=[conflict],
            timeline=[],
            metadata={},
            statistics={},
        )
        result = formatter.format(
            session_id="s",
            question="q",
            generation_result=_make_generation_result(),
            context_package=ctx,
            prompt_package=_make_prompt_package(),
            total_latency_ms=100.0,
        )
        assert len(result.conflicts) == 1
        assert "TT 01" in result.conflicts[0].description or "Mâu thuẫn" in result.conflicts[0].description
