from __future__ import annotations

from uuid import UUID

from app.domain.entities.chunk import Chunk
from app.domain.value_objects.chunk_type import ChunkType
from app.infrastructure.ingestion.chunkers.base_chunker import BaseChunker, estimate_tokens
from app.infrastructure.ingestion.parsed_document import ParsedDocument
from app.utils.uuid_utils import new_uuid


class SemanticChunker(BaseChunker):
    """Chunks documents by paragraph with configurable target size and overlap.

    Used for SOPs, Manuals, Policy documents.
    """

    def __init__(self, target_tokens: int = 300, overlap_tokens: int = 50) -> None:
        self._target = target_tokens
        self._overlap = overlap_tokens

    def chunk(self, document_id: UUID, parsed: ParsedDocument) -> list[Chunk]:
        # Split raw text into paragraphs
        paragraphs = [p.strip() for p in parsed.raw_text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in parsed.raw_text.split("\n") if p.strip()]

        chunks: list[Chunk] = []
        buffer: list[str] = []
        buffer_tokens = 0
        index = 0

        for para in paragraphs:
            para_tokens = estimate_tokens(para)

            if buffer_tokens + para_tokens > self._target and buffer:
                chunk_text = "\n\n".join(buffer)
                chunks.append(
                    Chunk(
                        id=new_uuid(),
                        document_id=document_id,
                        content=chunk_text,
                        chunk_index=index,
                        chunk_type=ChunkType.PARAGRAPH,
                        token_count=estimate_tokens(chunk_text),
                    )
                )
                index += 1

                # Keep overlap: retain last paragraph(s) up to overlap_tokens
                overlap_buf: list[str] = []
                overlap_tok = 0
                for p in reversed(buffer):
                    t = estimate_tokens(p)
                    if overlap_tok + t > self._overlap:
                        break
                    overlap_buf.insert(0, p)
                    overlap_tok += t
                buffer = overlap_buf
                buffer_tokens = overlap_tok

            buffer.append(para)
            buffer_tokens += para_tokens

        if buffer:
            chunk_text = "\n\n".join(buffer)
            chunks.append(
                Chunk(
                    id=new_uuid(),
                    document_id=document_id,
                    content=chunk_text,
                    chunk_index=index,
                    chunk_type=ChunkType.PARAGRAPH,
                    token_count=estimate_tokens(chunk_text),
                )
            )

        return chunks
