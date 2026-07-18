from __future__ import annotations

import asyncio
import re

import fitz  # PyMuPDF

from app.infrastructure.ingestion.ocr.ocr_provider import OCRProvider
from app.infrastructure.ingestion.parsed_document import ParsedDocument, ParsedSection
from app.infrastructure.ingestion.parsers.document_parser import DocumentParser

_DIEU_RE = re.compile(r"^(Điều\s+\d+)[\.\:]?\s*(.*)", re.IGNORECASE)


def _parse_sync(content: bytes, ocr: OCRProvider | None) -> ParsedDocument:
    doc = fitz.open(stream=content, filetype="pdf")
    all_text: list[str] = []
    sections: list[ParsedSection] = []
    current: ParsedSection | None = None
    title = ""
    page_count = len(doc)

    for page_num, page in enumerate(doc):
        page_text = page.get_text()
        if not page_text.strip() and ocr is not None:
            pass  # OCR would run here when is_available; skip for now

        for line in page_text.splitlines():
            line = line.strip()
            if not line:
                continue
            all_text.append(line)

            m = _DIEU_RE.match(line)
            if m:
                if current is not None:
                    sections.append(current)
                current = ParsedSection(
                    section_number=m.group(1),
                    section_title=m.group(2).strip(),
                    content="",
                    level=2,
                    page_number=page_num + 1,
                )
            elif current is not None:
                current.content += line + "\n"
            elif not title:
                title = line

    if current is not None:
        sections.append(current)

    raw_text = "\n".join(all_text)
    if not title and all_text:
        title = all_text[0]

    return ParsedDocument(
        title=title,
        raw_text=raw_text,
        sections=sections,
        page_count=page_count,
    )


class PdfParser(DocumentParser):
    def __init__(self, ocr: OCRProvider | None = None) -> None:
        self._ocr = ocr

    @property
    def supported_content_types(self) -> list[str]:
        return ["application/pdf"]

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        return await asyncio.to_thread(_parse_sync, content, self._ocr)
