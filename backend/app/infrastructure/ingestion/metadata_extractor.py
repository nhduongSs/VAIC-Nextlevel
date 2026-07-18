from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from app.infrastructure.ingestion.parsed_document import ParsedDocument

# Patterns for Vietnamese legal documents
_DOC_NUMBER_RE = re.compile(r"\b(\d{1,3}/\d{4}/[A-ZĐ]+-[A-ZĐ]+(?:-[A-ZĐ]+)*)\b")
_ISSUED_DATE_RE = re.compile(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", re.IGNORECASE)
_EFFECTIVE_DATE_RE = re.compile(
    r"(?:có hiệu lực|hiệu lực thi hành).*?ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
    re.IGNORECASE | re.DOTALL,
)
_ISSUING_BODY_PATTERNS = [
    "NGÂN HÀNG NHÀ NƯỚC VIỆT NAM",
    "BỘ TÀI CHÍNH",
    "CHÍNH PHỦ",
    "QUỐC HỘI",
    "ỦY BAN NHÂN DÂN",
]

_METADATA_HEADER_CHARS = 2000  # metadata is almost always in the document header


@dataclass
class ExtractedMetadata:
    doc_number: str | None
    issuing_body: str | None
    issued_date: date | None
    effective_date: date | None
    expired_date: date | None
    language: str
    page_count: int


class MetadataExtractor:
    """Extracts structured metadata from parsed Vietnamese legal documents using regex."""

    def extract(self, parsed: ParsedDocument) -> ExtractedMetadata:
        text = parsed.raw_text
        header = text[:_METADATA_HEADER_CHARS]

        doc_number = self._extract_doc_number(header) or self._extract_doc_number(text)
        issuing_body = self._extract_issuing_body(header)
        issued_date = self._extract_issued_date(header)
        effective_date = self._extract_effective_date(text)

        return ExtractedMetadata(
            doc_number=doc_number,
            issuing_body=issuing_body,
            issued_date=issued_date,
            effective_date=effective_date,
            expired_date=None,
            language=parsed.language,
            page_count=parsed.page_count,
        )

    def _extract_doc_number(self, text: str) -> str | None:
        m = _DOC_NUMBER_RE.search(text)
        return m.group(1) if m else None

    def _extract_issuing_body(self, text: str) -> str | None:
        upper = text.upper()
        for body in _ISSUING_BODY_PATTERNS:
            if body in upper:
                return body.title()
        return None

    def _extract_issued_date(self, text: str) -> date | None:
        m = _ISSUED_DATE_RE.search(text)
        if m:
            try:
                return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                return None
        return None

    def _extract_effective_date(self, text: str) -> date | None:
        m = _EFFECTIVE_DATE_RE.search(text)
        if m:
            try:
                return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                return None
        return None
