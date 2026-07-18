"""Unit tests for SearchService validation and orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.dto.search_dto import SearchRequest
from app.application.services.search_service import SearchService
from app.domain.value_objects.search_result import SearchResult
from app.presentation.exceptions import AppException


def _make_result(score: float = 0.9) -> SearchResult:
    return SearchResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        content="Văn bản pháp lý NHNN",
        score=score,
        retrieval_method="hybrid",
    )


def _make_service() -> tuple[SearchService, AsyncMock]:
    session = MagicMock()
    provider = AsyncMock()
    provider.health_check = AsyncMock(return_value=True)
    return SearchService(session=session, provider=provider), provider


@pytest.mark.asyncio
async def test_empty_query_raises() -> None:
    svc, _ = _make_service()
    with pytest.raises(AppException) as exc_info:
        await svc.search(SearchRequest(query="   "))
    assert exc_info.value.error == "INVALID_QUERY"
    assert "empty" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_query_too_long_raises() -> None:
    svc, _ = _make_service()
    long_query = "q" * 1001
    with pytest.raises(AppException) as exc_info:
        await svc.search(SearchRequest(query=long_query))
    assert exc_info.value.error == "INVALID_QUERY"
    assert "length" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_top_k_zero_raises() -> None:
    svc, _ = _make_service()
    with pytest.raises(AppException) as exc_info:
        await svc.search(SearchRequest(query="test", top_k=0))
    assert exc_info.value.error == "INVALID_QUERY"


@pytest.mark.asyncio
async def test_top_k_exceeds_max_raises() -> None:
    svc, _ = _make_service()
    with pytest.raises(AppException) as exc_info:
        await svc.search(SearchRequest(query="test", top_k=999))
    assert exc_info.value.error == "INVALID_QUERY"


@pytest.mark.asyncio
async def test_invalid_vector_weight_raises() -> None:
    svc, _ = _make_service()
    with pytest.raises(AppException) as exc_info:
        await svc.search(SearchRequest(query="test", vector_weight=1.5))
    assert exc_info.value.error == "INVALID_QUERY"
    assert "vector_weight" in exc_info.value.message


@pytest.mark.asyncio
async def test_invalid_bm25_weight_raises() -> None:
    svc, _ = _make_service()
    with pytest.raises(AppException) as exc_info:
        await svc.search(SearchRequest(query="test", bm25_weight=-0.1))
    assert exc_info.value.error == "INVALID_QUERY"
    assert "bm25_weight" in exc_info.value.message


@pytest.mark.asyncio
async def test_successful_search_returns_results() -> None:
    svc, _ = _make_service()
    expected = [_make_result(0.9), _make_result(0.7)]

    with patch("app.application.services.search_service.HybridRetriever") as mock_hybrid:
        mock_instance = AsyncMock()
        mock_instance.retrieve = AsyncMock(return_value=expected)
        mock_hybrid.return_value = mock_instance

        results = await svc.search(SearchRequest(query="quy định vay vốn"))

    assert results == expected


@pytest.mark.asyncio
async def test_whitespace_query_is_stripped() -> None:
    svc, _ = _make_service()

    with patch("app.application.services.search_service.HybridRetriever") as mock_hybrid:
        mock_instance = AsyncMock()
        mock_instance.retrieve = AsyncMock(return_value=[])
        mock_hybrid.return_value = mock_instance

        results = await svc.search(SearchRequest(query="  lãi suất  "))

    assert results == []
    # retrieve was called with stripped query
    call_kwargs = mock_instance.retrieve.call_args
    assert call_kwargs.kwargs["query"] == "lãi suất"


@pytest.mark.asyncio
async def test_custom_weights_passed_to_hybrid() -> None:
    svc, _ = _make_service()

    with patch("app.application.services.search_service.HybridRetriever") as mock_hybrid:
        mock_instance = AsyncMock()
        mock_instance.retrieve = AsyncMock(return_value=[])
        mock_hybrid.return_value = mock_instance

        await svc.search(SearchRequest(query="test", vector_weight=0.6, bm25_weight=0.4))

    constructor_call = mock_hybrid.call_args
    assert constructor_call.kwargs["alpha"] == 0.6
    assert constructor_call.kwargs["beta"] == 0.4


@pytest.mark.asyncio
async def test_health_delegates_to_provider() -> None:
    svc, provider = _make_service()
    result = await svc.health()
    assert result is True
    provider.health_check.assert_awaited_once()


@pytest.mark.asyncio
async def test_empty_results_logged_without_error() -> None:
    svc, _ = _make_service()

    with patch("app.application.services.search_service.HybridRetriever") as mock_hybrid:
        mock_instance = AsyncMock()
        mock_instance.retrieve = AsyncMock(return_value=[])
        mock_hybrid.return_value = mock_instance

        results = await svc.search(SearchRequest(query="no match query"))

    assert results == []
