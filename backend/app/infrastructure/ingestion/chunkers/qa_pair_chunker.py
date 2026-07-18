"""QAPairChunker — splits FAQ-style documents into Q&A pairs."""
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

_QA_RE = re.compile(r"(Câu hỏi\s*\d*[:.]|Q\s*\d*[:.])(.+?)(?=Câu hỏi\s*\d*[:.:]|Q\s*\d*[:.:]|$)", re.DOTALL | re.IGNORECASE)


class QAPairChunker:
    def chunk(self, document_id: UUID, parsed: "ParsedDocument") -> list[Chunk]:
        now = datetime.now(UTC)
        chunks: list[Chunk] = []

        for m in _QA_RE.finditer(parsed.raw_text):
            content = (m.group(1) + m.group(2)).strip()
            if len(content) >= 50:
                chunks.append(
                    Chunk(
                        id=uuid.uuid4(),
                        document_id=document_id,
                        content=content,
                        chunk_index=len(chunks),
                        chunk_type=ChunkType.PARAGRAPH,
                        token_count=len(content) // 4,
                        created_at=now,
                    )
                )

        if not chunks:
            semantic = __import__(
                "app.infrastructure.ingestion.chunkers.semantic_chunker",
                fromlist=["SemanticChunker"],
            ).SemanticChunker()
            chunks = semantic.chunk(document_id=document_id, parsed=parsed)

        return chunks
