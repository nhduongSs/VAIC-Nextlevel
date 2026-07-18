"""Tests for Wave 4 prompt-building pipeline."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.generation.prompt.builder import PromptBuilder
from app.generation.prompt.config import PromptConfig, PromptType
from app.generation.prompt.optimizer import PromptOptimizer
from app.generation.prompt.token_estimator import TokenEstimator
from app.models.enums import SearchResult
from app.services.document_relation_service import (
    Citation,
    ContextPackage,
    ConflictInfo,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    content: str = "Nội dung điều khoản mẫu",
    score: float = 0.8,
    chunk_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=document_id or uuid.uuid4(),
        content=content,
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
        metadata={
            "doc_number": "01/2024/TT-NHNN",
            "document_title": "Thông tư 01",
            "effective_date": "2024-01-01",
        },
    )


def _make_citation(
    chunk_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
) -> Citation:
    cid = chunk_id or uuid.uuid4()
    did = document_id or uuid.uuid4()
    return Citation(
        chunk_id=cid,
        document_id=did,
        document_title="Thông tư 01",
        doc_number="01/2024/TT-NHNN",
        section_title="Điều 1",
        section_number="1",
        page_number=1,
        chunk_index=0,
        authority_level="NHNN_CIRCULAR",
        version=1,
        effective_date=None,
        content_preview="Nội dung điều khoản mẫu",
    )


def _empty_package(query: str = "Lãi suất tiết kiệm là bao nhiêu?") -> ContextPackage:
    return ContextPackage(
        query=query,
        ranked_chunks=[],
        citations=[],
        relationships=[],
        conflicts=[],
        timeline=[],
        metadata={},
        statistics={},
    )


def _package_with_chunks(n: int = 3) -> ContextPackage:
    chunks = [_make_chunk(content=f"Chunk {i}") for i in range(n)]
    citations = [
        _make_citation(chunk_id=chunks[i].chunk_id, document_id=chunks[i].document_id)
        for i in range(n)
    ]
    return ContextPackage(
        query="Lãi suất cho vay là bao nhiêu?",
        ranked_chunks=chunks,
        citations=citations,
        relationships=[],
        conflicts=[],
        timeline=[],
        metadata={},
        statistics={},
    )


# ---------------------------------------------------------------------------
# TokenEstimator
# ---------------------------------------------------------------------------


class TestTokenEstimator:
    def test_estimate_empty(self) -> None:
        est = TokenEstimator()
        # Empty string → minimum 1 token
        assert est.estimate("") == 1

    def test_estimate_4_chars_1_token(self) -> None:
        est = TokenEstimator()
        # 40 chars → ~10 tokens
        result = est.estimate("a" * 40)
        assert result == 10

    def test_estimate_returns_int(self) -> None:
        est = TokenEstimator()
        assert isinstance(est.estimate("hello world"), int)

    def test_estimate_prompt_includes_overhead(self) -> None:
        est = TokenEstimator()
        system = "a" * 400  # 100 tokens
        user = "b" * 40  # 10 tokens
        result = est.estimate_prompt(system, user)
        # 100 + 10 + 20 overhead = 130
        assert result == 130

    def test_estimate_completion_returns_max_tokens(self) -> None:
        est = TokenEstimator()
        assert est.estimate_completion(2048) == 2048

    def test_estimate_vietnamese_text(self) -> None:
        est = TokenEstimator()
        text = "Lãi suất tiết kiệm không kỳ hạn"
        result = est.estimate(text)
        # Should be > 0 and reasonable
        assert result > 0
        assert result < len(text)


# ---------------------------------------------------------------------------
# PromptOptimizer
# ---------------------------------------------------------------------------


class TestPromptOptimizer:
    def test_deduplicate_chunks(self) -> None:
        shared_id = uuid.uuid4()
        chunk_a = _make_chunk(content="Version A", chunk_id=shared_id)
        chunk_b = _make_chunk(content="Version B", chunk_id=shared_id)
        package = ContextPackage(
            query="test",
            ranked_chunks=[chunk_a, chunk_b],
            citations=[],
            relationships=[],
            conflicts=[],
            timeline=[],
            metadata={},
            statistics={},
        )
        optimizer = PromptOptimizer()
        result = optimizer.optimize(package)
        assert len(result.ranked_chunks) == 1
        assert result.ranked_chunks[0].content == "Version A"

    def test_deduplicate_citations(self) -> None:
        shared_cit_id = uuid.uuid4()
        cit_a = _make_citation(chunk_id=shared_cit_id)
        cit_b = _make_citation(chunk_id=shared_cit_id)
        package = ContextPackage(
            query="test",
            ranked_chunks=[],
            citations=[cit_a, cit_b],
            relationships=[],
            conflicts=[],
            timeline=[],
            metadata={},
            statistics={},
        )
        optimizer = PromptOptimizer()
        result = optimizer.optimize(package)
        assert len(result.citations) == 1

    def test_limit_chunks_to_max(self) -> None:
        chunks = [_make_chunk(content=f"Chunk {i}") for i in range(20)]
        package = ContextPackage(
            query="test",
            ranked_chunks=chunks,
            citations=[],
            relationships=[],
            conflicts=[],
            timeline=[],
            metadata={},
            statistics={},
        )
        config = PromptConfig(max_context_chunks=5)
        optimizer = PromptOptimizer(config=config)
        result = optimizer.optimize(package)
        assert len(result.ranked_chunks) <= 5

    def test_truncates_when_over_budget(self) -> None:
        # Create a chunk that is very long
        long_chunk = _make_chunk(content="x" * 50000)  # ~12500 tokens
        package = ContextPackage(
            query="test",
            ranked_chunks=[long_chunk],
            citations=[],
            relationships=[],
            conflicts=[],
            timeline=[],
            metadata={},
            statistics={},
        )
        config = PromptConfig(max_prompt_tokens=500)  # very tight budget
        optimizer = PromptOptimizer(config=config)
        result = optimizer.optimize(package)
        # Either truncated or was_truncated is True
        assert result.was_truncated or (
            len(result.ranked_chunks) == 0
            or len(result.ranked_chunks[0].content) < 50000
        )

    def test_empty_package_returns_empty(self) -> None:
        optimizer = PromptOptimizer()
        result = optimizer.optimize(_empty_package())
        assert result.ranked_chunks == []
        assert result.citations == []
        assert result.was_truncated is False


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------


class TestPromptBuilder:
    def test_build_empty_package_returns_valid_package(self) -> None:
        builder = PromptBuilder()
        package = builder.build(_empty_package())
        assert package.system_prompt
        assert package.user_prompt
        assert package.estimated_prompt_tokens > 0
        assert package.estimated_total_tokens > 0
        assert package.context_chunks_used == 0
        assert package.was_truncated is False

    def test_build_with_chunks_context_in_prompt(self) -> None:
        builder = PromptBuilder()
        pkg = _package_with_chunks(n=2)
        result = builder.build(pkg)
        # Context block should appear in system prompt
        assert "Chunk 0" in result.system_prompt or "Đoạn 1" in result.system_prompt

    def test_build_respects_prompt_type(self) -> None:
        builder = PromptBuilder()
        pkg = _empty_package()
        qa_result = builder.build(pkg, prompt_type=PromptType.QA)
        sum_result = builder.build(pkg, prompt_type=PromptType.SUMMARIZATION)
        # User prompts should differ between types
        assert qa_result.user_prompt != sum_result.user_prompt

    def test_all_four_prompt_types_differ(self) -> None:
        builder = PromptBuilder()
        pkg = _empty_package()
        prompts = {
            pt: builder.build(pkg, prompt_type=pt).user_prompt
            for pt in PromptType
        }
        # All four user prompts should be unique
        unique = set(prompts.values())
        assert len(unique) == 4

    def test_build_returns_correct_chunks_used(self) -> None:
        builder = PromptBuilder()
        pkg = _package_with_chunks(n=3)
        result = builder.build(pkg)
        assert result.context_chunks_used == 3

    def test_build_prompt_type_stored_correctly(self) -> None:
        builder = PromptBuilder()
        pkg = _empty_package()
        result = builder.build(pkg, prompt_type=PromptType.COMPARISON)
        assert result.prompt_type == PromptType.COMPARISON

    def test_build_config_attached_to_package(self) -> None:
        config = PromptConfig(max_context_chunks=7)
        builder = PromptBuilder(config=config)
        result = builder.build(_empty_package())
        assert result.config.max_context_chunks == 7
