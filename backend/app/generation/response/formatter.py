"""ResponseFormatter — converts GenerationResult + ContextPackage into AnswerPackage."""
from __future__ import annotations

import structlog

from app.generation.llm.deepseek_service import GenerationResult
from app.generation.prompt.package import PromptPackage
from app.generation.response.citation_formatter import CitationFormatter
from app.generation.response.package import AnswerPackage, UsageStatistics
from app.models.schemas import ChatResponse, ConflictInfo as ConflictInfoSchema, Source
from app.services.document_relation_service import ContextPackage

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class ResponseFormatter:
    """Assembles an :class:`AnswerPackage` from all pipeline outputs."""

    def __init__(self, citation_formatter: CitationFormatter | None = None) -> None:
        self._citation_fmt = citation_formatter or CitationFormatter()

    def format(
        self,
        session_id: str,
        question: str,
        generation_result: GenerationResult,
        context_package: ContextPackage,
        prompt_package: PromptPackage,
        total_latency_ms: float,
    ) -> AnswerPackage:
        """Build an :class:`AnswerPackage` from all pipeline outputs."""

        # ── Build sources ──────────────────────────────────────────────────
        chunk_map = {
            str(chunk.chunk_id): chunk
            for chunk in context_package.ranked_chunks
        }
        sources: list[Source] = []
        for cit in context_package.citations:
            chunk = chunk_map.get(str(cit.chunk_id))
            sources.append(
                self._citation_fmt.to_source_schema(citation=cit, chunk=chunk)
            )

        # ── Build conflicts (schema version) ───────────────────────────────
        conflicts: list[ConflictInfoSchema] = [
            ConflictInfoSchema(
                description=cf.description or f"{cf.source_title} vs {cf.target_title}",
                conflicting_sources=[
                    str(cf.source_doc_id),
                    str(cf.target_doc_id),
                ],
            )
            for cf in context_package.conflicts
        ]

        # ── Usage statistics ───────────────────────────────────────────────
        usage = UsageStatistics.from_tokens(
            prompt_tokens=generation_result.prompt_tokens,
            completion_tokens=generation_result.completion_tokens,
            retry_count=generation_result.retry_count,
            provider=generation_result.provider,
            model=generation_result.model,
        )

        # ── Confidence score ───────────────────────────────────────────────
        # Heuristic: average of top-3 chunk scores, clamped to [0, 1]
        top_chunks = sorted(
            context_package.ranked_chunks, key=lambda c: c.score, reverse=True
        )[:3]
        if top_chunks:
            raw_score = sum(c.score for c in top_chunks) / len(top_chunks)
            confidence = max(0.0, min(1.0, raw_score))
        else:
            confidence = 0.0

        log.info(
            "response_formatter_done",
            session_id=session_id,
            sources_count=len(sources),
            conflicts_count=len(conflicts),
            confidence_score=round(confidence, 4),
            usage_total_tokens=usage.total_tokens,
            estimated_cost_usd=usage.estimated_cost_usd,
            latency_ms=round(total_latency_ms, 1),
            provider=generation_result.provider,
            model=generation_result.model,
        )

        return AnswerPackage(
            session_id=session_id,
            question=question,
            answer=generation_result.content,
            sources=sources,
            conflicts=conflicts,
            usage=usage,
            prompt_type=prompt_package.prompt_type,
            confidence_score=round(confidence, 4),
            latency_ms=round(total_latency_ms, 1),
            provider=generation_result.provider,
            model=generation_result.model,
        )

    def to_chat_response(self, answer_package: AnswerPackage) -> ChatResponse:
        """Convert an :class:`AnswerPackage` to the standard :class:`ChatResponse`."""
        return ChatResponse(
            session_id=answer_package.session_id,
            answer=answer_package.answer,
            sources=answer_package.sources,
            conflicts=answer_package.conflicts,
            blocked=answer_package.blocked,
            block_reason=answer_package.block_reason,
        )
