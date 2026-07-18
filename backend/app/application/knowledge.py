from __future__ import annotations

import time
from typing import Protocol

import structlog

from app.application.dto.knowledge_dto import ContextPackage, KnowledgeContext

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class KnowledgeProcessor(Protocol):
    async def process(self, context: KnowledgeContext) -> None: ...


class KnowledgePipeline:
    """Executes a sequence of KnowledgeProcessors against a shared KnowledgeContext."""

    def __init__(self, processors: list[KnowledgeProcessor]) -> None:
        self._processors = list(processors)

    def add_processor(self, processor: KnowledgeProcessor) -> None:
        self._processors.append(processor)

    async def execute(self, context: KnowledgeContext) -> ContextPackage:
        t0 = time.perf_counter()
        for processor in self._processors:
            pt0 = time.perf_counter()
            name = type(processor).__name__
            await processor.process(context)
            pt_ms = (time.perf_counter() - pt0) * 1000
            log.debug("processor_executed", processor=name, latency_ms=round(pt_ms, 1))

        total_ms = (time.perf_counter() - t0) * 1000
        context.statistics["pipeline_latency_ms"] = round(total_ms, 1)

        if context.context_package is None:
            raise RuntimeError(
                "Pipeline produced no ContextPackage — "
                "ensure ContextBuilderProcessor is the last processor"
            )
        log.info(
            "pipeline_complete",
            processors=len(self._processors),
            latency_ms=round(total_ms, 1),
        )
        return context.context_package
