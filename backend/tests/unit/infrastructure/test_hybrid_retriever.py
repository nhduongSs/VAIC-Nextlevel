"""Unit tests for HybridRetriever — BM25 and Vector are mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.retrieval.hybrid_retriever import HybridRetriever


def _result(score: float, method: str = "bm25") -> SearchResult:
    return SearchResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        content="test content",
        score=score,
        retrieval_method=method,
        bm25_score=score if method == "bm25" else None,
        vector_score=score if method == "vector" else None,
    )


def _shared_result(
    chunk_id: object, bm25_score: float = 0.8, vector_score: float = 0.9
) -> tuple[SearchResult, SearchResult]:
    cid = chunk_id  # type: ignore[assignment]
    doc_id = uuid4()
    b = SearchResult(
        chunk_id=cid,
        document_id=doc_id,
        content="shared chunk",
        score=bm25_score,
        retrieval_method="bm25",
        bm25_score=bm25_score,
    )
    v = SearchResult(
        chunk_id=cid,
        document_id=doc_id,
        content="shared chunk",
        score=vector_score,
        retrieval_method="vector",
        vector_score=vector_score,
    )
    return b, v


@pytest.mark.asyncio
async def test_empty_results_from_both() -> None:
    bm25 = AsyncMock()
    bm25.retrieve = AsyncMock(return_value=[])
    vector = AsyncMock()
    vector.retrieve = AsyncMock(return_value=[])

    hybrid = HybridRetriever(bm25=bm25, vector=vector)
    results = await hybrid.retrieve("test query", top_k=5)
    assert results == []


@pytest.mark.asyncio
async def test_only_bm25_results() -> None:
    bm25 = AsyncMock()
    bm25.retrieve = AsyncMock(return_value=[_result(0.5), _result(0.3)])
    vector = AsyncMock()
    vector.retrieve = AsyncMock(return_value=[])

    hybrid = HybridRetriever(bm25=bm25, vector=vector, alpha=0.7, beta=0.3)
    results = await hybrid.retrieve("test", top_k=5)
    assert len(results) == 2
    assert all(r.retrieval_method == "hybrid" for r in results)
    assert results[0].score >= results[1].score


@pytest.mark.asyncio
async def test_only_vector_results() -> None:
    bm25 = AsyncMock()
    bm25.retrieve = AsyncMock(return_value=[])
    vector = AsyncMock()
    vector.retrieve = AsyncMock(return_value=[_result(0.9, "vector"), _result(0.4, "vector")])

    hybrid = HybridRetriever(bm25=bm25, vector=vector, alpha=0.7, beta=0.3)
    results = await hybrid.retrieve("test", top_k=5)
    assert len(results) == 2
    assert results[0].score >= results[1].score


@pytest.mark.asyncio
async def test_shared_chunk_scores_combined() -> None:
    cid = uuid4()
    b_res, v_res = _shared_result(cid, bm25_score=1.0, vector_score=1.0)

    bm25 = AsyncMock()
    bm25.retrieve = AsyncMock(return_value=[b_res])
    vector = AsyncMock()
    vector.retrieve = AsyncMock(return_value=[v_res])

    hybrid = HybridRetriever(bm25=bm25, vector=vector, alpha=0.7, beta=0.3)
    results = await hybrid.retrieve("test", top_k=5)

    # One unique chunk — both scores applied
    assert len(results) == 1
    merged = results[0]
    assert merged.chunk_id == cid
    assert merged.bm25_score is not None
    assert merged.vector_score is not None
    # score ≈ 0.7 * 1.0 + 0.3 * 1.0 = 1.0 (after min-max both equal 1.0)
    assert merged.score == pytest.approx(1.0, abs=0.01)


@pytest.mark.asyncio
async def test_top_k_limits_results() -> None:
    bm25 = AsyncMock()
    bm25.retrieve = AsyncMock(return_value=[_result(float(i) / 10) for i in range(10)])
    vector = AsyncMock()
    vector.retrieve = AsyncMock(return_value=[])

    hybrid = HybridRetriever(bm25=bm25, vector=vector)
    results = await hybrid.retrieve("test", top_k=3)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_results_sorted_descending() -> None:
    bm25 = AsyncMock()
    bm25.retrieve = AsyncMock(return_value=[_result(0.2), _result(0.8), _result(0.5)])
    vector = AsyncMock()
    vector.retrieve = AsyncMock(return_value=[])

    hybrid = HybridRetriever(bm25=bm25, vector=vector)
    results = await hybrid.retrieve("test", top_k=10)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_deduplication() -> None:
    cid = uuid4()
    b1, v1 = _shared_result(cid)

    bm25 = AsyncMock()
    bm25.retrieve = AsyncMock(return_value=[b1])
    vector = AsyncMock()
    vector.retrieve = AsyncMock(return_value=[v1])

    hybrid = HybridRetriever(bm25=bm25, vector=vector)
    results = await hybrid.retrieve("test", top_k=10)
    chunk_ids = [r.chunk_id for r in results]
    assert len(chunk_ids) == len(set(chunk_ids)), "Duplicate chunk_ids found"
