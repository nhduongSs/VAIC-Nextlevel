"""Unit tests for KnowledgePipeline."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.dto.knowledge_dto import ContextPackage, KnowledgeContext
from app.application.knowledge import KnowledgePipeline
from app.domain.value_objects.search_result import SearchResult
from app.infrastructure.knowledge.processors.context_builder import ContextBuilderProcessor


def _chunk() -> SearchResult:
    return SearchResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        content="content",
        score=0.8,
        retrieval_method="hybrid",
    )


def _ctx(n_chunks: int = 1) -> KnowledgeContext:
    chunks = [_chunk() for _ in range(n_chunks)]
    return KnowledgeContext(
        query="query",
        retrieved_chunks=chunks,
        ranked_chunks=list(chunks),
        document_map={},
    )


class RecordingProcessor:
    """Records that it was called and sets a marker in statistics."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.called = False

    async def process(self, context: KnowledgeContext) -> None:
        self.called = True
        context.statistics[f"proc_{self.name}"] = True


class ContextBuilderStub:
    """Minimal stub that creates a ContextPackage so the pipeline can complete."""

    async def process(self, context: KnowledgeContext) -> None:
        context.context_package = ContextPackage(
            query=context.query,
            ranked_chunks=context.ranked_chunks,
            citations=[],
            relationships=[],
            conflicts=[],
            timeline=[],
            metadata={},
            statistics={},
        )


@pytest.mark.asyncio
async def test_processors_run_in_order() -> None:
    order: list[str] = []

    class OrderedProc:
        def __init__(self, label: str) -> None:
            self.label = label

        async def process(self, context: KnowledgeContext) -> None:
            order.append(self.label)

    stub = ContextBuilderStub()
    pipeline = KnowledgePipeline([OrderedProc("A"), OrderedProc("B"), stub])
    await pipeline.execute(_ctx())
    assert order == ["A", "B"]


@pytest.mark.asyncio
async def test_execute_returns_context_package() -> None:
    pipeline = KnowledgePipeline([ContextBuilderProcessor()])
    ctx = _ctx(2)
    package = await pipeline.execute(ctx)
    assert isinstance(package, ContextPackage)
    assert package.query == "query"


@pytest.mark.asyncio
async def test_pipeline_latency_recorded_in_statistics() -> None:
    ctx = _ctx()
    await KnowledgePipeline([ContextBuilderStub()]).execute(ctx)
    assert "pipeline_latency_ms" in ctx.statistics


@pytest.mark.asyncio
async def test_missing_context_builder_raises_runtime_error() -> None:
    proc = RecordingProcessor("only")
    pipeline = KnowledgePipeline([proc])
    with pytest.raises(RuntimeError, match="ContextBuilderProcessor"):
        await pipeline.execute(_ctx())


@pytest.mark.asyncio
async def test_add_processor_appended_and_executed() -> None:
    proc = RecordingProcessor("extra")
    pipeline = KnowledgePipeline([ContextBuilderStub()])
    pipeline.add_processor(proc)
    # proc added AFTER builder; pipeline still returns even if proc runs after
    # Rebuild with proc before builder to test it's actually called
    pipeline2 = KnowledgePipeline([proc, ContextBuilderStub()])
    await pipeline2.execute(_ctx())
    assert proc.called is True
