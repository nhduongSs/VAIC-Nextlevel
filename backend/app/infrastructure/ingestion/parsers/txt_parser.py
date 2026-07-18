"""TxtParser — parses plain-text files."""
from __future__ import annotations

from app.infrastructure.ingestion.parsed_document import ParsedDocument, ParsedSection


class TxtParser:
    supported_content_types: list[str] = ["text/plain"]

    def __init__(self, ocr: object = None) -> None:
        pass

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        text = content.decode("utf-8", errors="replace")
        sections = [ParsedSection(number=None, title=None, content=text)]
        return ParsedDocument(raw_text=text, sections=sections, page_count=1)
