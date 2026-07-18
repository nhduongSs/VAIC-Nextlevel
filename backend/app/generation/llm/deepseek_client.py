"""DeepSeekClient — AsyncOpenAI-compatible client with retry and streaming."""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

import openai
import structlog
from openai import AsyncOpenAI

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class DeepSeekClient:
    """OpenAI-compatible client targeting the DeepSeek API.

    Features
    --------
    - Configurable retry count with exponential back-off
    - Per-request timeout passed to ``AsyncOpenAI``
    - Streaming via ``stream=True``
    - Handles: timeout, rate-limit (429), connection errors, generic API errors
    - **Never logs API keys or full prompt text**
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
        retry_count: int = 2,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self._model = model
        self._retry_count = retry_count

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        top_p: float = 0.9,
    ) -> tuple[str, dict[str, int]]:
        """Call the chat completion endpoint with retry logic.

        Returns:
            ``(content, usage_dict)`` where *usage_dict* has keys
            ``prompt_tokens``, ``completion_tokens``, ``total_tokens``.
        """
        last_exc: Exception | None = None

        for attempt in range(self._retry_count + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )

                content = (
                    response.choices[0].message.content or ""
                ).strip()

                usage: dict[str, int] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }
                if response.usage is not None:
                    usage["prompt_tokens"] = response.usage.prompt_tokens or 0
                    usage["completion_tokens"] = response.usage.completion_tokens or 0
                    usage["total_tokens"] = response.usage.total_tokens or 0

                log.debug(
                    "deepseek_generate_success",
                    model=self._model,
                    attempt=attempt,
                    prompt_tokens=usage["prompt_tokens"],
                    completion_tokens=usage["completion_tokens"],
                )
                return content, usage

            except (
                openai.APITimeoutError,
                openai.RateLimitError,
                openai.APIConnectionError,
                openai.APIError,
            ) as exc:
                last_exc = exc
                log.warning(
                    "deepseek_generate_error",
                    error_type=type(exc).__name__,
                    attempt=attempt,
                    max_attempts=self._retry_count,
                )
                if attempt < self._retry_count:
                    backoff = 2 ** attempt
                    await asyncio.sleep(backoff)

        raise RuntimeError(
            f"DeepSeek generate failed after {self._retry_count + 1} attempts"
        ) from last_exc

    async def stream_generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        top_p: float = 0.9,
    ) -> AsyncGenerator[str, None]:
        """Yield text tokens as they arrive from the streaming API."""
        log.debug("deepseek_stream_start", model=self._model)
        async with await self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        ) as stream:
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content

    async def health_check(self) -> bool:
        """Return *True* if the client is properly configured.

        Performs a minimal validation without making a real API call.
        """
        try:
            # A simple attribute access is enough to confirm the client is set up.
            _ = self._client.base_url
            return True
        except Exception:
            return False
