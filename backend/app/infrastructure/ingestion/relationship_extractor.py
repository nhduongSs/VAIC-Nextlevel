"""RelationshipExtractor — extracts legal document relationships from raw text."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RawRelation:
    target_doc_number: str
    relation_type: str
    confidence: float
    description: str | None = None


_REPLACES_RE = re.compile(
    r"thay thế.*?(\d{1,3}/\d{4}/(?:TT|QĐ|NĐ|CT)-\w+)",
    re.IGNORECASE,
)
_AMENDS_RE = re.compile(
    r"sửa đổi.*?(\d{1,3}/\d{4}/(?:TT|QĐ|NĐ|CT)-\w+)",
    re.IGNORECASE,
)


class RelationshipExtractor:
    def extract(self, raw_text: str) -> list[RawRelation]:
        relations: list[RawRelation] = []
        for m in _REPLACES_RE.finditer(raw_text):
            relations.append(
                RawRelation(
                    target_doc_number=m.group(1),
                    relation_type="REPLACES",
                    confidence=0.85,
                    description=f"Thay thế {m.group(1)}",
                )
            )
        for m in _AMENDS_RE.finditer(raw_text):
            relations.append(
                RawRelation(
                    target_doc_number=m.group(1),
                    relation_type="AMENDS",
                    confidence=0.8,
                    description=f"Sửa đổi {m.group(1)}",
                )
            )
        return relations
