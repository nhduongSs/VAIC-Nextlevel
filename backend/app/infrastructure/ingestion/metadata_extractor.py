"""MetadataExtractor — extracts structured metadata from parsed documents."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.ingestion.parsed_document import ParsedDocument

_DOC_NUMBER_RE = re.compile(
    r"\b(\d{1,3}/\d{4}/(?:TT|QĐ|NĐ|CT)-(?:NHNN|BTC|CP|TTg)\b)",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", re.IGNORECASE)


@dataclass
class ExtractedMetadata:
    doc_number: str | None = None
    issuing_body: str | None = None
    issued_date: date | None = None
    effective_date: date | None = None


class MetadataExtractor:
    def extract(self, parsed: "ParsedDocument") -> ExtractedMetadata:
        text = parsed.raw_text[:2000]

        doc_number: str | None = None
        m = _DOC_NUMBER_RE.search(text)
        if m:
            doc_number = m.group(1)

        issuing_body: str | None = None
        if "ngân hàng nhà nước" in text.lower():
            issuing_body = "Ngân hàng Nhà nước Việt Nam"

        issued_date: date | None = None
        dm = _DATE_RE.search(text)
        if dm:
            try:
                issued_date = date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1)))
            except ValueError:
                pass

        return ExtractedMetadata(
            doc_number=doc_number,
            issuing_body=issuing_body,
            issued_date=issued_date,
            effective_date=issued_date,
        )
