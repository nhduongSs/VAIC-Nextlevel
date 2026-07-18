"""PromptBuilder — main entry point for Wave 4 prompt construction."""
from __future__ import annotations

from app.generation.prompt.config import PromptConfig, PromptType
from app.generation.prompt.optimizer import PromptOptimizer
from app.generation.prompt.package import PromptPackage
from app.generation.prompt.renderer import PromptRenderer
from app.generation.prompt.template import PromptTemplate
from app.generation.prompt.token_estimator import TokenEstimator
from app.services.document_relation_service import ContextPackage


class PromptBuilder:
    """Orchestrates the full prompt-building pipeline.

    Steps:
    1. Optimize context (deduplicate, count-limit, token-budget truncation)
    2. Render context string from chunks + timeline + conflicts
    3. Fill system & user templates
    4. Estimate final token counts
    5. Return a :class:`PromptPackage`
    """

    def __init__(
        self,
        config: PromptConfig | None = None,
        estimator: TokenEstimator | None = None,
        optimizer: PromptOptimizer | None = None,
        renderer: PromptRenderer | None = None,
    ) -> None:
        self._config = config or PromptConfig()
        self._estimator = estimator or TokenEstimator()
        self._optimizer = optimizer or PromptOptimizer(
            config=self._config, estimator=self._estimator
        )
        self._renderer = renderer or PromptRenderer()

    def build(
        self,
        context_package: ContextPackage,
        prompt_type: PromptType = PromptType.QA,
    ) -> PromptPackage:
        """Build a :class:`PromptPackage` from *context_package*."""

        # ── 1. Optimize ────────────────────────────────────────────────────
        optimized = self._optimizer.optimize(context_package)

        # ── 2. Render context string ───────────────────────────────────────
        context_str = self._renderer.render_context(
            chunks=optimized.ranked_chunks,
            conflicts=context_package.conflicts,
            timeline=context_package.timeline,
            config=self._config,
        )

        # ── 3. Fill templates ──────────────────────────────────────────────
        template = PromptTemplate.for_type(prompt_type)

        conflict_section = self._renderer.render_conflict_section_for_user(
            conflicts=context_package.conflicts,
            config=self._config,
        )

        system_prompt = self._renderer.render_system_prompt(
            template=template,
            context_str=context_str,
        )
        user_prompt = self._renderer.render_user_prompt(
            template=template,
            question=context_package.query,
            conflict_section=conflict_section,
        )

        # ── 4. Estimate tokens ─────────────────────────────────────────────
        estimated_prompt_tokens = self._estimator.estimate_prompt(
            system_prompt, user_prompt
        )
        estimated_completion_tokens = self._estimator.estimate_completion(
            self._config.max_completion_tokens
        )
        estimated_total_tokens = estimated_prompt_tokens + estimated_completion_tokens

        # ── 5. Return package ──────────────────────────────────────────────
        return PromptPackage(
            prompt_type=prompt_type,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            estimated_prompt_tokens=estimated_prompt_tokens,
            estimated_completion_tokens=estimated_completion_tokens,
            estimated_total_tokens=estimated_total_tokens,
            context_chunks_used=len(optimized.ranked_chunks),
            citations_used=len(optimized.citations),
            was_truncated=optimized.was_truncated,
            config=self._config,
        )
