from __future__ import annotations

import re
from uuid import UUID

from app.domain.entities.chunk import Chunk
from app.domain.value_objects.chunk_type import ChunkType
from app.infrastructure.ingestion.chunkers.base_chunker import BaseChunker, estimate_tokens
from app.infrastructure.ingestion.parsed_document import ParsedDocument
from app.utils.uuid_utils import new_uuid

_Q_RE = re.compile(
    r"^(?:Q\s*[:：]|Câu\s+hỏi\s*[:：]|\d+[\.\)]\s*Câu\s+hỏi|^\d+[\.\)]\s+)",  # noqa: RUF001
    re.IGNORECASE | re.MULTILINE,
)
_A_RE = re.compile(
    r"^(?:A\s*[:：]|Trả\s+lời\s*[:：]|Đáp\s*[:：])",  # noqa: RUF001
    re.IGNORECASE | re.MULTILINE,
)


class QAPairChunker(BaseChunker):
    """Chunks FAQ documents as Q+A pairs."""

    def chunk(self, document_id: UUID, parsed: ParsedDocument) -> list[Chunk]:
        chunks = self._try_qa_split(document_id, parsed.raw_text)
        if not chunks:
            chunks = self._split_by_section(document_id, parsed)
        return chunks

    def _try_qa_split(self, document_id: UUID, text: str) -> list[Chunk]:
        q_positions = [m.start() for m in _Q_RE.finditer(text)]
        if len(q_positions) < 2:
            return []

        chunks: list[Chunk] = []
        for i, start in enumerate(q_positions):
            end = q_positions[i + 1] if i + 1 < len(q_positions) else len(text)
            pair = text[start:end].strip()
            if pair:
                chunks.append(
                    Chunk(
                        id=new_uuid(),
                        document_id=document_id,
                        content=pair,
                        chunk_index=i,
                        chunk_type=ChunkType.PARAGRAPH,
                        token_count=estimate_tokens(pair),
                    )
                )
        return chunks

    def _split_by_section(self, document_id: UUID, parsed: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        for i, section in enumerate(parsed.sections):
            text = section.full_text()
            chunks.append(
                Chunk(
                    id=new_uuid(),
                    document_id=document_id,
                    content=text,
                    chunk_index=i,
                    chunk_type=ChunkType.PARAGRAPH,
                    section_number=section.section_number or None,
                    section_title=section.section_title or None,
                    token_count=estimate_tokens(text),
                )
            )
        if not chunks and parsed.raw_text.strip():
            chunks.append(
                Chunk(
                    id=new_uuid(),
                    document_id=document_id,
                    content=parsed.raw_text[:8000],
                    chunk_index=0,
                    chunk_type=ChunkType.PARAGRAPH,
                    token_count=estimate_tokens(parsed.raw_text[:8000]),
                )
            )
        return chunks
