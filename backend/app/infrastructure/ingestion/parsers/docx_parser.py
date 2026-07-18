"""DocxParser — parses Word DOCX files."""
from __future__ import annotations

from app.infrastructure.ingestion.parsed_document import ParsedDocument, ParsedSection

_DOCX_TYPES = [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
]


class DocxParser:
    supported_content_types: list[str] = _DOCX_TYPES

    def __init__(self, ocr: object = None) -> None:
        self._ocr = ocr

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        try:
            import docx  # type: ignore[import-untyped]
            import io

            doc = docx.Document(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            raw_text = "\n".join(paragraphs)
            sections = [ParsedSection(number=None, title=None, content=raw_text)]
            return ParsedDocument(raw_text=raw_text, sections=sections, page_count=1)
        except ImportError:
            raw_text = content.decode("utf-8", errors="replace")
            return ParsedDocument(
                raw_text=raw_text,
                sections=[ParsedSection(number=None, title=None, content=raw_text)],
                page_count=1,
            )
