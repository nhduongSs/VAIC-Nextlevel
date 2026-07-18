"""DocumentClassifier — classifies documents by type and authority level."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Classification:
    doc_type: str
    authority_level: str


_TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("thông tư", "CIRCULAR"),
    ("quyết định", "DECISION"),
    ("nghị định", "DECREE"),
    ("luật", "LAW"),
    ("faq", "FAQ"),
    ("hỏi đáp", "FAQ"),
    ("quy trình", "SOP"),
    ("hướng dẫn", "MANUAL"),
]

_AUTHORITY_KEYWORDS: list[tuple[str, str]] = [
    ("nhnn", "NHNN_CIRCULAR"),
    ("ngân hàng nhà nước", "NHNN_CIRCULAR"),
    ("quốc hội", "NATIONAL_LAW"),
    ("chính phủ", "NHNN_DECISION"),
]


class DocumentClassifier:
    def classify(
        self,
        raw_text: str,
        doc_number: str | None = None,
        issuing_body: str | None = None,
    ) -> Classification:
        text_lower = (raw_text[:1000] + " " + (doc_number or "") + " " + (issuing_body or "")).lower()

        doc_type = "UNKNOWN"
        for kw, dt in _TYPE_KEYWORDS:
            if kw in text_lower:
                doc_type = dt
                break

        authority_level = "UNKNOWN"
        for kw, al in _AUTHORITY_KEYWORDS:
            if kw in text_lower:
                authority_level = al
                break

        if doc_type == "CIRCULAR" and authority_level == "NHNN_CIRCULAR":
            authority_level = "NHNN_CIRCULAR"

        return Classification(doc_type=doc_type, authority_level=authority_level)
