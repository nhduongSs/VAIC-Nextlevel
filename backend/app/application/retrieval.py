from __future__ import annotations

from typing import Protocol

from app.application.dto.search_dto import SearchFilters
from app.domain.value_objects.search_result import SearchResult


class Retriever(Protocol):
    async def retrieve(
        self,
        query: str,
        filters: SearchFilters | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]: ...


class RetrieverFactory(Protocol):
    def create(self, *, alpha: float, beta: float) -> Retriever: ...
