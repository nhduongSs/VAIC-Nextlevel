"""Unit tests for KnowledgeIntelligenceService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.dto.knowledge_dto import ContextPackage
from app.application.services.knowledge_service import KnowledgeIntelligenceService, _empty_package
from app.config import Settings
from app.domain.value_objects.search_result import SearchResult


def _settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql+asyncpg://x:x@localhost/x",
        EMBEDDING_SERVICE_URL="http://localhost:8001",
        KI_EXPANSION_DEPTH=1,
        KI_MAX_RELATIONS=5,
        KI_MAX_CITATIONS=5,
        KI_MAX_CONTEXT_CHUNKS=10,
        KI_TIMELINE_ENABLED=True,
        KI_CITATION_ENABLED=True,
        KI_CONFLICT_DETECTION_ENABLED=True,
        KI_AUTHORITY_WEIGHT=0.2,
    )


def _chunk(doc_id: object = None) -> SearchResult:
    return SearchResult(
        chunk_id=uuid4(),
        document_id=doc_id or uuid4(),  # type: ignore[arg-type]
        content="content",
        score=0.8,
        retrieval_method="hybrid",
    )


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    # _fetch_documents / _fetch_relations both do session.execute(stmt)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    return session


@pytest.mark.asyncio
async def test_empty_results_returns_empty_package() -> None:
    session = _mock_session()
    svc = KnowledgeIntelligenceService(session, _settings())
    pkg = await svc.process("query", [])
    assert pkg.ranked_chunks == []
    assert pkg.citations == []
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_process_returns_context_package() -> None:
    session = _mock_session()
    svc = KnowledgeIntelligenceService(session, _settings())

    chunk = _chunk()
    pkg = await svc.process("query", [chunk])

    assert isinstance(pkg, ContextPackage)
    assert pkg.query == "query"


@pytest.mark.asyncio
async def test_process_deduplicates_doc_ids_for_fetch() -> None:
    doc_id = uuid4()
    session = _mock_session()
    svc = KnowledgeIntelligenceService(session, _settings())

    chunks = [_chunk(doc_id) for _ in range(3)]
    await svc.process("query", chunks)

    # execute called twice: once for docs, once for relations
    assert session.execute.call_count == 2


@pytest.mark.asyncio
async def test_health_returns_true_on_success() -> None:
    session = _mock_session()
    svc = KnowledgeIntelligenceService(session, _settings())
    result = await svc.health()
    assert result is True


@pytest.mark.asyncio
async def test_health_returns_false_on_db_error() -> None:
    session = AsyncMock()
    session.execute.side_effect = Exception("DB down")
    svc = KnowledgeIntelligenceService(session, _settings())
    result = await svc.health()
    assert result is False


def test_empty_package_helper() -> None:
    pkg = _empty_package("q")
    assert pkg.query == "q"
    assert pkg.ranked_chunks == []
    assert pkg.statistics["ranked_chunk_count"] == 0
