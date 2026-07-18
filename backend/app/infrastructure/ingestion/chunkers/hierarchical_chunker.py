from __future__ import annotations

from uuid import UUID

from app.domain.entities.chunk import Chunk
from app.domain.value_objects.chunk_type import ChunkType
from app.infrastructure.ingestion.chunkers.base_chunker import BaseChunker, estimate_tokens
from app.infrastructure.ingestion.parsed_document import ParsedDocument, ParsedSection
from app.utils.uuid_utils import new_uuid


class HierarchicalChunker(BaseChunker):
    """Chunks Vietnamese legal documents at Điều (article) level.

    If an article exceeds max_tokens it is split by Khoản (clause).
    """

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 50) -> None:
        self._max_tokens = max_tokens
        self._overlap_tokens = overlap_tokens

    def chunk(self, document_id: UUID, parsed: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        index = 0

        # Use Điều-level sections (level 2); fall back to all sections if none found
        dieu_sections = [s for s in parsed.sections if s.level == 2]
        sections_to_chunk = dieu_sections if dieu_sections else parsed.sections

        for section in sections_to_chunk:
            new_chunks, index = self._section_to_chunks(document_id, section, index)
            chunks.extend(new_chunks)

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

    def _section_to_chunks(
        self,
        document_id: UUID,
        section: ParsedSection,
        start_index: int,
    ) -> tuple[list[Chunk], int]:
        full_text = section.full_text()
        token_count = estimate_tokens(full_text)
        index = start_index

        if token_count <= self._max_tokens:
            chunk = Chunk(
                id=new_uuid(),
                document_id=document_id,
                content=full_text,
                chunk_index=index,
                chunk_type=ChunkType.ARTICLE,
                section_number=section.section_number or None,
                section_title=section.section_title or None,
                page_number=section.page_number or None,
                token_count=token_count,
            )
            return [chunk], index + 1

        # Split by clauses (children) when article is too long
        chunks: list[Chunk] = []
        if section.children:
            for child in section.children:
                child_text = child.full_text()
                child_tokens = estimate_tokens(child_text)
                chunk = Chunk(
                    id=new_uuid(),
                    document_id=document_id,
                    content=child_text,
                    chunk_index=index,
                    chunk_type=ChunkType.CLAUSE,
                    section_number=f"{section.section_number} {child.section_number}".strip(),
                    section_title=section.section_title or None,
                    page_number=child.page_number or section.page_number or None,
                    token_count=child_tokens,
                )
                chunks.append(chunk)
                index += 1
        else:
            # No children — split by words with overlap
            words = full_text.split()
            pos = 0
            while pos < len(words):
                window = words[pos : pos + self._max_tokens]
                text_slice = " ".join(window)
                chunk = Chunk(
                    id=new_uuid(),
                    document_id=document_id,
                    content=text_slice,
                    chunk_index=index,
                    chunk_type=ChunkType.CLAUSE,
                    section_number=section.section_number or None,
                    section_title=section.section_title or None,
                    page_number=section.page_number or None,
                    token_count=len(window),
                )
                chunks.append(chunk)
                index += 1
                pos += self._max_tokens - self._overlap_tokens

        return chunks, index
