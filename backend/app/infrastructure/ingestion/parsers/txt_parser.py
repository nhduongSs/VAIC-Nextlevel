from __future__ import annotations

import asyncio
import re

from app.infrastructure.ingestion.parsed_document import ParsedDocument, ParsedSection
from app.infrastructure.ingestion.parsers.document_parser import DocumentParser

_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$")
_DIEU_RE = re.compile(r"^(Điều\s+\d+)[\.\:]?\s*(.*)", re.IGNORECASE)


def _parse_sync(content: bytes) -> ParsedDocument:
    text = content.decode("utf-8", errors="replace")
    lines = text.splitlines()
    sections: list[ParsedSection] = []
    current: ParsedSection | None = None
    title = ""
    all_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        all_lines.append(stripped)

        md_match = _HEADING_RE.match(stripped)
        dieu_match = _DIEU_RE.match(stripped)

        if md_match or dieu_match:
            if current is not None:
                sections.append(current)
            if md_match:
                section_title = md_match.group(1).strip()
                current = ParsedSection(
                    section_number="",
                    section_title=section_title,
                    content="",
                    level=2,
                )
            elif dieu_match:
                current = ParsedSection(
                    section_number=dieu_match.group(1),
                    section_title=dieu_match.group(2).strip(),
                    content="",
                    level=2,
                )
        elif current is not None:
            current.content += stripped + "\n"
        elif not title:
            title = stripped

    if current is not None:
        sections.append(current)

    raw_text = "\n".join(all_lines)
    if not title and all_lines:
        title = all_lines[0]

    return ParsedDocument(
        title=title,
        raw_text=raw_text,
        sections=sections,
        page_count=1,
    )


class TxtParser(DocumentParser):
    @property
    def supported_content_types(self) -> list[str]:
        return ["text/plain", "text/markdown"]

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        return await asyncio.to_thread(_parse_sync, content)
