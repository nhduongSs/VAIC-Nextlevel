"""Prompt configuration — PromptType enum and PromptConfig dataclass."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PromptType(str, Enum):
    QA = "qa"
    SUMMARIZATION = "summarization"
    COMPARISON = "comparison"
    EXPLANATION = "explanation"


@dataclass
class PromptConfig:
    prompt_type: PromptType = PromptType.QA
    max_prompt_tokens: int = 6000
    max_completion_tokens: int = 2048
    max_context_chunks: int = 10
    max_citations: int = 10
    include_timeline: bool = True
    include_conflicts: bool = True
    include_relationships: bool = False
    language: str = "vi"
