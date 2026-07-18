"""Unit tests for BgeM3Client — HTTP calls are mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.ai.embedding.bge_m3_client import BgeM3Client


@pytest.fixture
def client() -> BgeM3Client:
    return BgeM3Client(base_url="http://embedding-service:8001")


def _mock_response(embeddings: list[list[float]]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"embeddings": embeddings, "model": "BAAI/bge-m3"}
    return resp


@pytest.mark.asyncio
async def test_embed_empty_list_returns_empty(client: BgeM3Client) -> None:
    result = await client.embed([])
    assert result == []


@pytest.mark.asyncio
async def test_embed_returns_correct_count(client: BgeM3Client) -> None:
    texts = ["a", "b", "c"]
    vectors = [[0.1] * 1024 for _ in texts]
    mock_resp = _mock_response(vectors)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch(
        "app.infrastructure.ai.embedding.bge_m3_client.httpx.AsyncClient", return_value=mock_client
    ):
        result = await client.embed(texts)

    assert len(result) == 3
    assert all(len(v) == 1024 for v in result)


@pytest.mark.asyncio
async def test_embed_raises_on_count_mismatch(client: BgeM3Client) -> None:
    texts = ["a", "b"]
    vectors = [[0.1] * 1024]  # only 1 vector for 2 texts
    mock_resp = _mock_response(vectors)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch(
        "app.infrastructure.ai.embedding.bge_m3_client.httpx.AsyncClient", return_value=mock_client
    ):
        with pytest.raises(ValueError, match="Embedding count mismatch"):
            await client.embed(texts)


@pytest.mark.asyncio
async def test_embed_raises_on_wrong_dimension(client: BgeM3Client) -> None:
    texts = ["a"]
    vectors = [[0.1] * 512]  # wrong: 512 instead of 1024
    mock_resp = _mock_response(vectors)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch(
        "app.infrastructure.ai.embedding.bge_m3_client.httpx.AsyncClient", return_value=mock_client
    ):
        with pytest.raises(ValueError, match="512 dimensions, expected 1024"):
            await client.embed(texts)


@pytest.mark.asyncio
async def test_health_check_returns_true_on_200(client: BgeM3Client) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch(
        "app.infrastructure.ai.embedding.bge_m3_client.httpx.AsyncClient", return_value=mock_client
    ):
        result = await client.health_check()

    assert result is True


@pytest.mark.asyncio
async def test_health_check_returns_false_on_exception(client: BgeM3Client) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=ConnectionError("refused"))

    with patch(
        "app.infrastructure.ai.embedding.bge_m3_client.httpx.AsyncClient", return_value=mock_client
    ):
        result = await client.health_check()

    assert result is False


def test_model_name(client: BgeM3Client) -> None:
    assert client.model_name == "BAAI/bge-m3"


def test_dimensions(client: BgeM3Client) -> None:
    assert client.dimensions == 1024
