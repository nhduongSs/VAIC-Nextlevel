from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedSection:
    section_number: str
    section_title: str
    content: str
    level: int  # 1=Chương, 2=Điều, 3=Khoản, 4=Điểm
    page_number: int = 0
    children: list[ParsedSection] = field(default_factory=list)

    def full_text(self) -> str:
        parts = []
        header = f"{self.section_number}. {self.section_title}".strip(". ")
        if header:
            parts.append(header)
        if self.content:
            parts.append(self.content)
        for child in self.children:
            parts.append(child.full_text())
        return "\n".join(parts)


@dataclass
class ParsedDocument:
    title: str
    raw_text: str
    sections: list[ParsedSection] = field(default_factory=list)
    page_count: int = 0
    language: str = "vi"
    needs_ocr: bool = False
