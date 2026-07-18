from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.value_objects.relation_type import RelationType

_DOC_NUMBER_PATTERN = r"(\d{1,3}/\d{4}/[A-ZĐa-zđ]+-[A-ZĐa-zđ]+(?:-[A-ZĐa-zđ]+)*)"

_PATTERNS: dict[RelationType, list[str]] = {
    RelationType.REPLACES: [
        r"thay thế[^.]*?" + _DOC_NUMBER_PATTERN,
        r"bãi bỏ[^.]*?" + _DOC_NUMBER_PATTERN,
        r"hết hiệu lực[^.]*?" + _DOC_NUMBER_PATTERN,
    ],
    RelationType.AMENDS: [
        r"sửa đổi[^.]*?" + _DOC_NUMBER_PATTERN,
        r"bổ sung[^.]*?" + _DOC_NUMBER_PATTERN,
    ],
    RelationType.REFERENCES: [
        r"căn cứ[^.]*?" + _DOC_NUMBER_PATTERN,
        r"theo quy định[^.]*?" + _DOC_NUMBER_PATTERN,
        r"theo.*?quy định tại[^.]*?" + _DOC_NUMBER_PATTERN,
    ],
}

_COMPILED: dict[RelationType, list[re.Pattern[str]]] = {
    rel_type: [re.compile(p, re.IGNORECASE) for p in patterns]
    for rel_type, patterns in _PATTERNS.items()
}


@dataclass
class ExtractedRelation:
    target_doc_number: str
    relation_type: RelationType
    confidence: float
    description: str | None = None


class RelationshipExtractor:
    """Extracts explicit document references from Vietnamese legal text."""

    def extract(self, raw_text: str) -> list[ExtractedRelation]:
        results: list[ExtractedRelation] = []
        seen: set[tuple[RelationType, str]] = set()

        for rel_type, patterns in _COMPILED.items():
            for pattern in patterns:
                for match in pattern.finditer(raw_text):
                    doc_number = match.group(1).upper()
                    key = (rel_type, doc_number)
                    if key not in seen:
                        seen.add(key)
                        confidence = 0.9 if rel_type == RelationType.REPLACES else 0.75
                        results.append(
                            ExtractedRelation(
                                target_doc_number=doc_number,
                                relation_type=rel_type,
                                confidence=confidence,
                            )
                        )

        return results
