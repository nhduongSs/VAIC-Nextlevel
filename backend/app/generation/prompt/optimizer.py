"""PromptOptimizer — deduplicates and truncates context to fit the token budget."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.generation.prompt.config import PromptConfig
from app.generation.prompt.token_estimator import TokenEstimator
from app.services.document_relation_service import Citation, ContextPackage
from app.models.enums import SearchResult


@dataclass
class OptimizedContext:
    """Slimmed-down context ready for rendering."""

    ranked_chunks: list[SearchResult]
    citations: list[Citation]
    was_truncated: bool


class PromptOptimizer:
    """Removes duplicates, enforces count limits, and truncates to the token budget."""

    def __init__(
        self,
        config: PromptConfig | None = None,
        estimator: TokenEstimator | None = None,
    ) -> None:
        self._config = config or PromptConfig()
        self._estimator = estimator or TokenEstimator()

    def optimize(self, context_package: ContextPackage) -> OptimizedContext:
        """Return an :class:`OptimizedContext` that fits within the configured limits."""
        cfg = self._config

        # ── 1. Deduplicate chunks by chunk_id ──────────────────────────────
        seen_chunk_ids: set[UUID] = set()
        unique_chunks: list[SearchResult] = []
        for chunk in context_package.ranked_chunks:
            if chunk.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk.chunk_id)
                unique_chunks.append(chunk)

        # ── 2. Deduplicate citations by chunk_id ───────────────────────────
        seen_cit_ids: set[UUID] = set()
        unique_citations: list[Citation] = []
        for cit in context_package.citations:
            if cit.chunk_id not in seen_cit_ids:
                seen_cit_ids.add(cit.chunk_id)
                unique_citations.append(cit)

        # ── 3. Apply count limits ──────────────────────────────────────────
        limited_chunks = unique_chunks[: cfg.max_context_chunks]
        limited_citations = unique_citations[: cfg.max_citations]

        # ── 4. Check token budget and truncate chunk content if needed ─────
        was_truncated = False
        # Estimate overhead tokens (system prompt skeleton + user prompt shell)
        # Reserve ~1200 tokens for system template scaffolding and user prompt
        available_for_context = cfg.max_prompt_tokens - 1200
        if available_for_context < 0:
            available_for_context = 0

        chunks_after_truncation: list[SearchResult] = []
        tokens_used = 0
        for chunk in limited_chunks:
            chunk_tokens = self._estimator.estimate(chunk.content)
            if tokens_used + chunk_tokens <= available_for_context:
                chunks_after_truncation.append(chunk)
                tokens_used += chunk_tokens
            else:
                # Try to fit a truncated version
                remaining = available_for_context - tokens_used
                if remaining > 50:
                    # Truncate content to fit remaining budget (chars = tokens * 4)
                    max_chars = remaining * 4
                    truncated = _truncate_chunk(chunk, max_chars)
                    chunks_after_truncation.append(truncated)
                    was_truncated = True
                else:
                    was_truncated = True
                break

        return OptimizedContext(
            ranked_chunks=chunks_after_truncation,
            citations=limited_citations,
            was_truncated=was_truncated,
        )


def _truncate_chunk(chunk: SearchResult, max_chars: int) -> SearchResult:
    """Return a *shallow copy* of *chunk* with content truncated to *max_chars*."""
    truncated_content = chunk.content[:max_chars] + "…"
    return SearchResult(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        content=truncated_content,
        score=chunk.score,
        retrieval_method=chunk.retrieval_method,
        bm25_score=chunk.bm25_score,
        vector_score=chunk.vector_score,
        chunk_index=chunk.chunk_index,
        chunk_type=chunk.chunk_type,
        section_title=chunk.section_title,
        section_number=chunk.section_number,
        page_number=chunk.page_number,
        bank=chunk.bank,
        category=chunk.category,
        metadata=dict(chunk.metadata),
    )
