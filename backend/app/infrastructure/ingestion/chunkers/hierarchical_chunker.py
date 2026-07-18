"""HierarchicalChunker — splits documents by legal section hierarchy."""
from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from app.models.entities import Chunk
from app.models.enums import ChunkType

if TYPE_CHECKING:
    from app.infrastructure.ingestion.parsed_document import ParsedDocument

_SECTION_RE = re.compile(
    r"^(Điều\s+\d+|Chương\s+[IVXLC]+|Mục\s+\d+)\b",
    re.MULTILINE | re.IGNORECASE,
)

_MAX_CHUNK_CHARS = 2000


class HierarchicalChunker:
    def chunk(self, document_id: UUID, parsed: "ParsedDocument") -> list[Chunk]:
        chunks: list[Chunk] = []
        text = parsed.raw_text

        boundaries = [m.start() for m in _SECTION_RE.finditer(text)]
        if not boundaries:
            return self._fallback_chunks(document_id, text)

        boundaries.append(len(text))
        now = datetime.now(UTC)

        for i, start in enumerate(boundaries[:-1]):
            end = boundaries[i + 1]
            section_text = text[start:end].strip()
            if not section_text:
                continue

            header_match = _SECTION_RE.match(section_text)
            section_title = header_match.group(0) if header_match else None

            for j, chunk_start in enumerate(range(0, len(section_text), _MAX_CHUNK_CHARS)):
                content = section_text[chunk_start : chunk_start + _MAX_CHUNK_CHARS].strip()
                if content:
                    chunks.append(
                        Chunk(
                            id=uuid.uuid4(),
                            document_id=document_id,
                            content=content,
                            chunk_index=len(chunks),
                            chunk_type=ChunkType.ARTICLE,
                            section_title=section_title,
                            token_count=len(content) // 4,
                            created_at=now,
                        )
                    )
        return chunks

    def _fallback_chunks(self, document_id: UUID, text: str) -> list[Chunk]:
        now = datetime.now(UTC)
        return [
            Chunk(
                id=uuid.uuid4(),
                document_id=document_id,
                content=text[i : i + _MAX_CHUNK_CHARS].strip(),
                chunk_index=idx,
                chunk_type=ChunkType.CLAUSE,
                token_count=len(text[i : i + _MAX_CHUNK_CHARS]) // 4,
                created_at=now,
            )
            for idx, i in enumerate(range(0, len(text), _MAX_CHUNK_CHARS))
            if text[i : i + _MAX_CHUNK_CHARS].strip()
        ]
