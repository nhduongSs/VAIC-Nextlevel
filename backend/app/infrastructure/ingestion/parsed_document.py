"""ParsedDocument — result of parsing a document file."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedSection:
    number: str | None
    title: str | None
    content: str
    page_number: int | None = None


@dataclass
class ParsedDocument:
    raw_text: str
    sections: list[ParsedSection] = field(default_factory=list)
    page_count: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
