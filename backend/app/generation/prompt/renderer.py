"""PromptRenderer — assembles context string and fills prompt templates."""
from __future__ import annotations

from app.generation.prompt.config import PromptConfig, PromptType
from app.generation.prompt.optimizer import OptimizedContext
from app.generation.prompt.template import PromptTemplate
from app.models.enums import SearchResult
from app.services.document_relation_service import ConflictInfo, ContextPackage, TimelineEntry

_CHUNK_SEPARATOR = "\n\n---\n\n"


class PromptRenderer:
    """Renders the assembled prompt from an optimized context."""

    def render_context(
        self,
        chunks: list[SearchResult],
        conflicts: list[ConflictInfo],
        timeline: list[TimelineEntry],
        config: PromptConfig,
    ) -> str:
        """Build the full context string to inject into the system prompt."""
        parts: list[str] = []

        # ── Chunks ─────────────────────────────────────────────────────────
        for i, chunk in enumerate(chunks, start=1):
            parts.append(_format_chunk(i, chunk))

        context_body = _CHUNK_SEPARATOR.join(parts) if parts else "(Không có ngữ cảnh)"

        # ── Timeline section ───────────────────────────────────────────────
        timeline_section = ""
        if config.include_timeline and timeline:
            lines = ["## LỊCH SỬ PHIÊN BẢN"]
            for entry in timeline:
                status = "✓ Hiện hành" if entry.is_current else "✗ Đã thay thế"
                eff = str(entry.effective_date) if entry.effective_date else "Không rõ"
                issued = str(entry.issued_date) if entry.issued_date else "Không rõ"
                lines.append(
                    f"- {entry.doc_number or entry.document_title} "
                    f"(phiên bản {entry.version}) — "
                    f"Ban hành: {issued} | Hiệu lực: {eff} | {status}"
                )
            timeline_section = "\n\n" + "\n".join(lines)

        # ── Conflict section (appended to context) ─────────────────────────
        conflict_section = ""
        if config.include_conflicts and conflicts:
            lines = ["## CẢNH BÁO MÂU THUẪN"]
            for cf in conflicts:
                desc = cf.description or "Mâu thuẫn nội dung giữa hai văn bản"
                lines.append(f"- {cf.source_title} ⟷ {cf.target_title}: {desc}")
            conflict_section = "\n\n" + "\n".join(lines)

        return context_body + timeline_section + conflict_section

    def render_conflict_section_for_user(
        self,
        conflicts: list[ConflictInfo],
        config: PromptConfig,
    ) -> str:
        """Render the conflict warning block for the user prompt."""
        if not config.include_conflicts or not conflicts:
            return ""
        lines = ["## CẢNH BÁO MÂU THUẪN"]
        for cf in conflicts:
            desc = cf.description or "Mâu thuẫn nội dung giữa hai văn bản"
            lines.append(f"⚠️  {cf.source_title} ⟷ {cf.target_title}: {desc}")
        return "\n".join(lines) + "\n"

    def render_system_prompt(
        self,
        template: PromptTemplate,
        context_str: str,
    ) -> str:
        """Fill the system template with the rendered context string."""
        return template.system_template.format(context=context_str)

    def render_user_prompt(
        self,
        template: PromptTemplate,
        question: str,
        conflict_section: str,
    ) -> str:
        """Fill the user template with the question and optional conflict warning."""
        return template.user_template.format(
            question=question,
            conflict_section=conflict_section,
        )


def _format_chunk(index: int, chunk: SearchResult) -> str:
    """Format a single chunk into the context block."""
    doc_number = chunk.metadata.get("doc_number", "Không rõ số hiệu")
    document_title = chunk.metadata.get("document_title", "Không rõ tên văn bản")
    effective_date = chunk.metadata.get("effective_date", "Không rõ")
    superseded = chunk.metadata.get("superseded", False)
    superseded_note = "Đã bị thay thế" if superseded else "Còn hiệu lực"

    section_number = chunk.section_number or ""
    section_title = chunk.section_title or ""
    page = str(chunk.page_number) if chunk.page_number is not None else "Không rõ"

    return (
        f"[Đoạn {index}]\n"
        f"Nguồn: {doc_number} — {document_title}\n"
        f"Điều khoản: {section_number} {section_title}".strip()
        + f"\n"
        f"Trang: {page} | Hiệu lực: {effective_date} | Trạng thái: {superseded_note}\n"
        f"\n{chunk.content}"
    )
