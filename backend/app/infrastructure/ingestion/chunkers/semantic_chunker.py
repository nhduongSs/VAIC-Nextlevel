"""SemanticChunker — splits documents by paragraph boundaries."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from app.models.entities import Chunk
from app.models.enums import ChunkType

if TYPE_CHECKING:
    from app.infrastructure.ingestion.parsed_document import ParsedDocument

_MAX_CHUNK_CHARS = 1500
_MIN_CHUNK_CHARS = 100


class SemanticChunker:
    def chunk(self, document_id: UUID, parsed: "ParsedDocument") -> list[Chunk]:
        now = datetime.now(UTC)
        paragraphs = [p.strip() for p in parsed.raw_text.split("\n\n") if len(p.strip()) >= _MIN_CHUNK_CHARS]

        chunks: list[Chunk] = []
        buffer = ""
        for para in paragraphs:
            if len(buffer) + len(para) > _MAX_CHUNK_CHARS and buffer:
                chunks.append(
                    Chunk(
                        id=uuid.uuid4(),
                        document_id=document_id,
                        content=buffer.strip(),
                        chunk_index=len(chunks),
                        chunk_type=ChunkType.PARAGRAPH,
                        token_count=len(buffer) // 4,
                        created_at=now,
                    )
                )
                buffer = para
            else:
                buffer = (buffer + "\n\n" + para).strip() if buffer else para

        if buffer.strip():
            chunks.append(
                Chunk(
                    id=uuid.uuid4(),
                    document_id=document_id,
                    content=buffer.strip(),
                    chunk_index=len(chunks),
                    chunk_type=ChunkType.PARAGRAPH,
                    token_count=len(buffer) // 4,
                    created_at=now,
                )
            )
        return chunks
