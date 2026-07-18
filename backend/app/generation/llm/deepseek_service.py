"""DeepSeekService — high-level generation service wrapping DeepSeekClient."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import AsyncGenerator

import structlog

from app.generation.llm.deepseek_client import DeepSeekClient
from app.generation.prompt.package import PromptPackage

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


@dataclass
class GenerationResult:
    """Result returned by :class:`DeepSeekService.generate`."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    retry_count: int
    latency_ms: float
    provider: str = "deepseek"
    model: str = "deepseek-chat"


class DeepSeekService:
    """Wraps :class:`DeepSeekClient` with logging, latency tracking, and settings."""

    def __init__(
        self,
        client: DeepSeekClient,
        model: str = "deepseek-chat",
        temperature: float = 0.1,
        top_p: float = 0.9,
    ) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._top_p = top_p

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(self, prompt_package: PromptPackage) -> GenerationResult:
        """Generate a full response from *prompt_package*."""
        t0 = time.perf_counter()

        log.info(
            "deepseek_service_generate",
            prompt_type=prompt_package.prompt_type.value,
            estimated_prompt_tokens=prompt_package.estimated_prompt_tokens,
            estimated_total_tokens=prompt_package.estimated_total_tokens,
            context_chunks=prompt_package.context_chunks_used,
            model=self._model,
            provider="deepseek",
        )

        content, usage = await self._client.generate(
            system_prompt=prompt_package.system_prompt,
            user_prompt=prompt_package.user_prompt,
            temperature=self._temperature,
            max_tokens=prompt_package.config.max_completion_tokens,
            top_p=self._top_p,
        )

        latency_ms = (time.perf_counter() - t0) * 1000

        log.info(
            "deepseek_service_generate_done",
            latency_ms=round(latency_ms, 1),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            model=self._model,
            provider="deepseek",
        )

        return GenerationResult(
            content=content,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            retry_count=0,  # retry tracking is internal to DeepSeekClient
            latency_ms=round(latency_ms, 1),
            provider="deepseek",
            model=self._model,
        )

    async def stream_generate(
        self, prompt_package: PromptPackage
    ) -> AsyncGenerator[str, None]:
        """Yield text tokens from the streaming API."""
        log.info(
            "deepseek_service_stream_start",
            prompt_type=prompt_package.prompt_type.value,
            model=self._model,
            provider="deepseek",
        )
        async for token in self._client.stream_generate(
            system_prompt=prompt_package.system_prompt,
            user_prompt=prompt_package.user_prompt,
            temperature=self._temperature,
            max_tokens=prompt_package.config.max_completion_tokens,
            top_p=self._top_p,
        ):
            yield token

    async def health_check(self) -> bool:
        """Delegate health check to the underlying client."""
        return await self._client.health_check()
