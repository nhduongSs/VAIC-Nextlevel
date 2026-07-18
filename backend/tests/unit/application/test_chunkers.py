from uuid import uuid4

from app.domain.value_objects.chunk_type import ChunkType
from app.infrastructure.ingestion.chunkers.hierarchical_chunker import HierarchicalChunker
from app.infrastructure.ingestion.chunkers.qa_pair_chunker import QAPairChunker
from app.infrastructure.ingestion.chunkers.semantic_chunker import SemanticChunker
from app.infrastructure.ingestion.parsed_document import ParsedDocument, ParsedSection


def _doc(raw: str, sections: list[ParsedSection] | None = None) -> ParsedDocument:
    return ParsedDocument(
        title="Test",
        raw_text=raw,
        sections=sections or [],
        page_count=1,
    )


def _section(number: str, title: str, content: str, level: int = 2) -> ParsedSection:
    return ParsedSection(
        section_number=number,
        section_title=title,
        content=content,
        level=level,
    )


# ── HierarchicalChunker ───────────────────────────────────────────────────────


class TestHierarchicalChunker:
    def setup_method(self) -> None:
        self.chunker = HierarchicalChunker(max_tokens=512, overlap_tokens=50)
        self.doc_id = uuid4()

    def test_single_section_produces_one_chunk(self) -> None:
        section = _section("Điều 1", "Phạm vi áp dụng", "Nội dung điều 1.")
        chunks = self.chunker.chunk(self.doc_id, _doc("Điều 1. Nội dung", [section]))
        assert len(chunks) == 1
        assert chunks[0].chunk_type == ChunkType.ARTICLE

    def test_section_numbers_preserved(self) -> None:
        section = _section("Điều 5", "Điều kiện vay", "Người vay phải đủ 18 tuổi.")
        chunks = self.chunker.chunk(self.doc_id, _doc("", [section]))
        assert chunks[0].section_number == "Điều 5"
        assert chunks[0].section_title == "Điều kiện vay"

    def test_multiple_sections_produce_multiple_chunks(self) -> None:
        sections = [
            _section("Điều 1", "Phạm vi", "Nội dung 1."),
            _section("Điều 2", "Đối tượng", "Nội dung 2."),
            _section("Điều 3", "Điều kiện", "Nội dung 3."),
        ]
        chunks = self.chunker.chunk(self.doc_id, _doc("", sections))
        assert len(chunks) == 3

    def test_chunk_indices_are_sequential(self) -> None:
        sections = [_section(f"Điều {i}", f"Title {i}", "Content.") for i in range(1, 6)]
        chunks = self.chunker.chunk(self.doc_id, _doc("", sections))
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_fallback_chunk_when_no_sections(self) -> None:
        chunks = self.chunker.chunk(self.doc_id, _doc("Some raw text without sections."))
        assert len(chunks) == 1
        assert chunks[0].chunk_type == ChunkType.PARAGRAPH

    def test_oversized_section_splits_by_words(self) -> None:
        long_content = " ".join(["word"] * 600)
        section = _section("Điều 1", "Long Article", long_content)
        chunker = HierarchicalChunker(max_tokens=100, overlap_tokens=10)
        chunks = chunker.chunk(self.doc_id, _doc(long_content, [section]))
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.chunk_type == ChunkType.CLAUSE

    def test_each_chunk_has_document_id(self) -> None:
        section = _section("Điều 1", "Title", "Content.")
        chunks = self.chunker.chunk(self.doc_id, _doc("", [section]))
        assert all(c.document_id == self.doc_id for c in chunks)


# ── SemanticChunker ───────────────────────────────────────────────────────────


class TestSemanticChunker:
    def setup_method(self) -> None:
        self.chunker = SemanticChunker(target_tokens=50, overlap_tokens=10)
        self.doc_id = uuid4()

    def test_short_text_produces_one_chunk(self) -> None:
        chunks = self.chunker.chunk(self.doc_id, _doc("Short text only."))
        assert len(chunks) == 1
        assert chunks[0].chunk_type == ChunkType.PARAGRAPH

    def test_long_text_splits_into_multiple_chunks(self) -> None:
        # Create text with many double-newline separated paragraphs
        paragraphs = ["word " * 30 for _ in range(10)]
        text = "\n\n".join(paragraphs)
        chunks = self.chunker.chunk(self.doc_id, _doc(text))
        assert len(chunks) > 1

    def test_empty_text_produces_no_chunks(self) -> None:
        chunks = self.chunker.chunk(self.doc_id, _doc(""))
        assert chunks == []

    def test_chunk_indices_are_sequential(self) -> None:
        paragraphs = ["word " * 60 for _ in range(5)]
        text = "\n\n".join(paragraphs)
        chunks = self.chunker.chunk(self.doc_id, _doc(text))
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_each_chunk_has_token_count(self) -> None:
        chunks = self.chunker.chunk(self.doc_id, _doc("Token counting text here."))
        assert all(c.token_count is not None and c.token_count > 0 for c in chunks)


# ── QAPairChunker ─────────────────────────────────────────────────────────────


class TestQAPairChunker:
    def setup_method(self) -> None:
        self.chunker = QAPairChunker()
        self.doc_id = uuid4()

    def test_qa_pairs_detected_by_prefix(self) -> None:
        text = (
            "Câu hỏi: Điều kiện vay là gì?\n"
            "Trả lời: Phải đủ 18 tuổi.\n\n"
            "Câu hỏi: Lãi suất bao nhiêu?\n"
            "Trả lời: 8% mỗi năm.\n"
        )
        chunks = self.chunker.chunk(self.doc_id, _doc(text))
        assert len(chunks) == 2

    def test_fallback_to_section_when_no_qa_pattern(self) -> None:
        sections = [
            _section("1", "Phần 1", "Nội dung phần 1."),
            _section("2", "Phần 2", "Nội dung phần 2."),
        ]
        chunks = self.chunker.chunk(self.doc_id, _doc("", sections))
        assert len(chunks) == 2

    def test_fallback_to_raw_text_when_empty_sections(self) -> None:
        chunks = self.chunker.chunk(self.doc_id, _doc("Some raw text with no Q&A patterns."))
        assert len(chunks) == 1

    def test_chunk_indices_sequential(self) -> None:
        text = "\n\n".join([f"Câu hỏi: Q{i}?\nTrả lời: A{i}." for i in range(3)])
        chunks = self.chunker.chunk(self.doc_id, _doc(text))
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
