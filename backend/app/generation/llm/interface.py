"""LLMClient Protocol — defines the interface every LLM client must satisfy."""
from __future__ import annotations

from typing import Protocol, runtime_checkable
from collections.abc import AsyncGenerator


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM text-generation clients.

    All implementations must be fully async and must never log API keys.
    """

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        top_p: float = 0.9,
    ) -> tuple[str, dict[str, int]]:
        """Generate a response.

        Returns:
            A tuple of (content, usage_dict) where *usage_dict* contains
            ``prompt_tokens``, ``completion_tokens``, and ``total_tokens``.
        """
        ...

    async def stream_generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        top_p: float = 0.9,
    ) -> AsyncGenerator[str, None]:
        """Yield response tokens as they arrive (streaming mode)."""
        ...

    async def health_check(self) -> bool:
        """Return *True* if the client is configured and reachable."""
        ...
