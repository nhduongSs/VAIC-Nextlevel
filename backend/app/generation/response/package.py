"""AnswerPackage and UsageStatistics dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.generation.prompt.config import PromptType

# DeepSeek Chat pricing (as of 2025):
# Input:  $0.14  per 1 million tokens
# Output: $0.28  per 1 million tokens
_COST_PER_INPUT_TOKEN: float = 0.14 / 1_000_000
_COST_PER_OUTPUT_TOKEN: float = 0.28 / 1_000_000


@dataclass
class UsageStatistics:
    """Token usage and cost for a single generation call."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    retry_count: int
    provider: str
    model: str

    @classmethod
    def from_tokens(
        cls,
        prompt_tokens: int,
        completion_tokens: int,
        retry_count: int,
        provider: str,
        model: str,
    ) -> "UsageStatistics":
        cost = (
            prompt_tokens * _COST_PER_INPUT_TOKEN
            + completion_tokens * _COST_PER_OUTPUT_TOKEN
        )
        return cls(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=round(cost, 8),
            retry_count=retry_count,
            provider=provider,
            model=model,
        )


@dataclass
class AnswerPackage:
    """Complete answer ready to be serialised into a ChatResponse."""

    session_id: str
    question: str
    answer: str
    sources: list  # list[Source] — typed loosely to avoid circular imports
    conflicts: list  # list[ConflictInfo] (schema version)
    usage: UsageStatistics
    prompt_type: PromptType
    confidence_score: float
    latency_ms: float
    provider: str
    model: str
    blocked: bool = False
    block_reason: str = "none"
