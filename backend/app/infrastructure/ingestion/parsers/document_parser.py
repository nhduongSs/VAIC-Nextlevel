"""DocumentParser protocol — abstracts file parsing."""
from __future__ import annotations

from typing import Protocol

from app.infrastructure.ingestion.parsed_document import ParsedDocument


class DocumentParser(Protocol):
    supported_content_types: list[str]

    async def parse(self, content: bytes, filename: str) -> ParsedDocument: ...
