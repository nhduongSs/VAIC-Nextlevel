"""Tests for DeepSeekClient — mocks AsyncOpenAI to avoid real API calls."""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from app.generation.llm.deepseek_client import DeepSeekClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(retry_count: int = 2) -> DeepSeekClient:
    return DeepSeekClient(
        api_key="sk-test",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        timeout=5.0,
        retry_count=retry_count,
    )


def _mock_completion(content: str = "Test answer") -> MagicMock:
    usage = MagicMock()
    usage.prompt_tokens = 100
    usage.completion_tokens = 50
    usage.total_tokens = 150

    choice = MagicMock()
    choice.message.content = content

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


# ---------------------------------------------------------------------------
# DeepSeekClient.generate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_returns_content_and_usage() -> None:
    client = _make_client()
    mock_response = _mock_completion("Câu trả lời mẫu")

    with patch.object(
        client._client.chat.completions, "create", new=AsyncMock(return_value=mock_response)
    ):
        content, usage = await client.generate(
            system_prompt="System",
            user_prompt="User",
        )

    assert content == "Câu trả lời mẫu"
    assert usage["prompt_tokens"] == 100
    assert usage["completion_tokens"] == 50
    assert usage["total_tokens"] == 150


@pytest.mark.asyncio
async def test_generate_retries_on_timeout_error() -> None:
    """Should retry on APITimeoutError and succeed on the second attempt."""
    client = _make_client(retry_count=2)
    mock_response = _mock_completion("Success after retry")

    call_count = 0

    async def _side_effect(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise openai.APITimeoutError(request=MagicMock())
        return mock_response

    with patch.object(
        client._client.chat.completions, "create", new=AsyncMock(side_effect=_side_effect)
    ):
        with patch("asyncio.sleep", new=AsyncMock()):
            content, usage = await client.generate(
                system_prompt="System",
                user_prompt="User",
            )

    assert content == "Success after retry"
    assert call_count == 2


@pytest.mark.asyncio
async def test_generate_raises_after_max_retries() -> None:
    """Should raise RuntimeError after all retries are exhausted."""
    client = _make_client(retry_count=1)

    with patch.object(
        client._client.chat.completions,
        "create",
        new=AsyncMock(side_effect=openai.APITimeoutError(request=MagicMock())),
    ):
        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(RuntimeError, match="failed after"):
                await client.generate(
                    system_prompt="System",
                    user_prompt="User",
                )


@pytest.mark.asyncio
async def test_generate_retries_on_rate_limit() -> None:
    client = _make_client(retry_count=2)
    mock_response = _mock_completion("ok")

    call_count = 0

    async def _side_effect(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise openai.RateLimitError(
                message="rate limited",
                response=MagicMock(),
                body=None,
            )
        return mock_response

    with patch.object(
        client._client.chat.completions, "create", new=AsyncMock(side_effect=_side_effect)
    ):
        with patch("asyncio.sleep", new=AsyncMock()):
            content, _ = await client.generate("sys", "usr")

    assert content == "ok"
    assert call_count == 2


@pytest.mark.asyncio
async def test_generate_handles_none_content() -> None:
    """Should return empty string when model returns None content."""
    client = _make_client()
    mock_response = _mock_completion(None)  # type: ignore[arg-type]
    mock_response.choices[0].message.content = None

    with patch.object(
        client._client.chat.completions, "create", new=AsyncMock(return_value=mock_response)
    ):
        content, _ = await client.generate("sys", "usr")

    assert content == ""


# ---------------------------------------------------------------------------
# DeepSeekClient.stream_generate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_generate_yields_tokens() -> None:
    client = _make_client()

    tokens = ["Câu ", "trả ", "lời ", "mẫu"]

    async def _mock_stream() -> AsyncGenerator[MagicMock, None]:
        for t in tokens:
            chunk = MagicMock()
            chunk.choices[0].delta.content = t
            yield chunk

    # The streaming API uses an async context manager
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=_mock_stream())
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch.object(
        client._client.chat.completions, "create", new=AsyncMock(return_value=mock_ctx)
    ):
        collected: list[str] = []
        async for token in client.stream_generate("sys", "usr"):
            collected.append(token)

    assert collected == tokens


# ---------------------------------------------------------------------------
# DeepSeekClient.health_check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_returns_true_when_configured() -> None:
    client = _make_client()
    result = await client.health_check()
    assert result is True
