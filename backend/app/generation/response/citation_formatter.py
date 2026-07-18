"""CitationFormatter — converts Citation dataclasses to schema objects and strings."""
from __future__ import annotations

from app.models.enums import SearchResult
from app.models.schemas import Source
from app.services.document_relation_service import Citation


class CitationFormatter:
    """Formats :class:`Citation` objects into human-readable strings and schema objects."""

    def format_citation(self, citation: Citation, index: int) -> str:
        """Return a single numbered citation line.

        Format: ``[{index}] {doc_number}, {section_number} {section_title} — {preview}``
        """
        doc_number = citation.doc_number or "Unknown"
        section_parts: list[str] = []
        if citation.section_number:
            section_parts.append(citation.section_number)
        if citation.section_title:
            section_parts.append(citation.section_title)
        section_str = " ".join(section_parts) if section_parts else "—"
        preview = citation.content_preview.replace("\n", " ").strip()

        return f"[{index}] {doc_number}, {section_str} — {preview}"

    def format_citation_list(self, citations: list[Citation]) -> str:
        """Return a numbered list of all citations joined by newlines."""
        if not citations:
            return ""
        lines = [
            self.format_citation(cit, i + 1) for i, cit in enumerate(citations)
        ]
        return "\n".join(lines)

    def to_source_schema(
        self,
        citation: Citation,
        chunk: SearchResult | None = None,
    ) -> Source:
        """Convert a :class:`Citation` (and optional matching chunk) to a :class:`Source`."""
        effective_date = (
            str(citation.effective_date) if citation.effective_date else None
        )
        bank = chunk.bank if chunk is not None else None
        doc_class = chunk.metadata.get("doc_class") if chunk is not None else None

        # Build clause string
        clause_parts: list[str] = []
        if citation.section_number:
            clause_parts.append(citation.section_number)
        if citation.section_title:
            clause_parts.append(citation.section_title)
        clause = " ".join(clause_parts) if clause_parts else ""

        return Source(
            doc_id=str(citation.document_id),
            title=citation.document_title,
            clause=clause,
            effective_date=effective_date,
            bank=bank,
            doc_class=doc_class,
        )
