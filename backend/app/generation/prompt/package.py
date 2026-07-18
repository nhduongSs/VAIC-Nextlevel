"""PromptPackage — the assembled, token-estimated prompt ready for LLM."""
from __future__ import annotations

from dataclasses import dataclass

from app.generation.prompt.config import PromptConfig, PromptType


@dataclass
class PromptPackage:
    """Final assembled prompt with metadata for the generation layer."""

    prompt_type: PromptType
    system_prompt: str
    user_prompt: str
    estimated_prompt_tokens: int
    estimated_completion_tokens: int
    estimated_total_tokens: int
    context_chunks_used: int
    citations_used: int
    was_truncated: bool
    config: PromptConfig
