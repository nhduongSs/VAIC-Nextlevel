from __future__ import annotations

import structlog

from app.application.dto.knowledge_dto import KnowledgeContext
from app.domain.value_objects.authority_level import AuthorityLevel

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_DEFAULT_AUTHORITY_SCORES: dict[str, float] = {
    AuthorityLevel.NATIONAL_LAW: 1.0,
    AuthorityLevel.NHNN_CIRCULAR: 0.8,
    AuthorityLevel.NHNN_DECISION: 0.7,
    AuthorityLevel.INTERNAL_POLICY: 0.5,
    AuthorityLevel.DEPARTMENT_SOP: 0.3,
    AuthorityLevel.FAQ: 0.1,
    AuthorityLevel.UNKNOWN: 0.0,
}


class AuthorityRankingProcessor:
    """Boosts chunk scores based on the issuing document's authority level.

    Final score = (1 - weight) * retrieval_score + weight * authority_score
    """

    def __init__(
        self,
        authority_scores: dict[str, float] | None = None,
        authority_weight: float = 0.2,
    ) -> None:
        self._scores = authority_scores or _DEFAULT_AUTHORITY_SCORES
        self._weight = authority_weight

    async def process(self, context: KnowledgeContext) -> None:
        for chunk in context.ranked_chunks:
            doc = context.document_map.get(chunk.document_id)
            authority_score = self._scores.get(str(doc.authority_level), 0.0) if doc else 0.0
            chunk.score = (1.0 - self._weight) * chunk.score + self._weight * authority_score
            chunk.metadata["authority_score"] = round(authority_score, 4)
            if doc:
                chunk.metadata["authority_level"] = str(doc.authority_level)

        context.ranked_chunks.sort(key=lambda r: r.score, reverse=True)
        context.statistics["authority_ranking_applied"] = True
        log.debug("authority_ranking_done", chunks=len(context.ranked_chunks))
