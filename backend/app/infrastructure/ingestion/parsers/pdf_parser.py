"""PdfParser — parses PDF files (stub: extracts raw bytes as text)."""
from __future__ import annotations

from app.infrastructure.ingestion.parsed_document import ParsedDocument, ParsedSection


class PdfParser:
    supported_content_types: list[str] = ["application/pdf"]

    def __init__(self, ocr: object = None) -> None:
        self._ocr = ocr

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        try:
            import pypdf  # type: ignore[import-untyped]
            import io

            reader = pypdf.PdfReader(io.BytesIO(content))
            pages: list[str] = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            raw_text = "\n\n".join(pages)
            sections = [
                ParsedSection(number=None, title=f"Trang {i + 1}", content=p)
                for i, p in enumerate(pages)
                if p.strip()
            ]
            return ParsedDocument(
                raw_text=raw_text,
                sections=sections or [ParsedSection(number=None, title=None, content=raw_text)],
                page_count=len(reader.pages),
            )
        except ImportError:
            raw_text = content.decode("utf-8", errors="replace")
            return ParsedDocument(
                raw_text=raw_text,
                sections=[ParsedSection(number=None, title=None, content=raw_text)],
                page_count=1,
            )
