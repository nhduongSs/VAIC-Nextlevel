"""Unit tests for the 7 Knowledge Intelligence pipeline processors
(`app/services/document_relation_service.py`), theo yêu cầu test riêng cho:

  1. Authority Ranking   -> AuthorityRankingProcessor
  2. Relationship Expansion -> RelationshipExpansionProcessor
  3. Version Resolver    -> VersionResolutionProcessor
  4. Amendment Resolver  -> DocumentRelationService.apply_amendment
  5. Conflict Detection  -> ConflictDetectionProcessor (bản wired vào pipeline,
     KHÁC với `detect_conflicts()` không wired — xem test_document_relation.py)
  6. Citation Builder    -> CitationProcessor
  7. Timeline Builder    -> TimelineProcessor

Xem doc/KI_Pipeline_Test_Plan.md để biết ma trận test case đầy đủ và lý do
từng case tồn tại.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.models.entities import Document, DocumentRelation
from app.models.enums import AuthorityLevel, DocumentStatus, DocumentType, RelationType, SearchResult
from app.services.document_relation_service import (
    AuthorityRankingProcessor,
    CitationProcessor,
    ConflictDetectionProcessor,
    DocumentRelationService,
    KnowledgeContext,
    RelationshipExpansionProcessor,
    TimelineProcessor,
    VersionResolutionProcessor,
)

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

_DOC_A = UUID("00000000-0000-0000-0000-00000000000a")
_DOC_B = UUID("00000000-0000-0000-0000-00000000000b")
_DOC_C = UUID("00000000-0000-0000-0000-00000000000c")
_DOC_D = UUID("00000000-0000-0000-0000-00000000000d")


def _document(
    doc_id: UUID,
    *,
    authority_level: AuthorityLevel = AuthorityLevel.UNKNOWN,
    version: int = 1,
    doc_number: str | None = None,
    title: str = "Document",
    effective_date: date | None = None,
    issued_date: date | None = None,
) -> Document:
    now = datetime(2026, 1, 1)
    return Document(
        id=doc_id,
        title=title,
        filename="f.md",
        original_filename="f.md",
        content_type="text/markdown",
        file_size=10,
        file_path="f.md",
        content_hash=f"hash-{doc_id}",
        status=DocumentStatus.READY,
        version=version,
        doc_type=DocumentType.LAW,
        authority_level=authority_level,
        created_at=now,
        updated_at=now,
        doc_number=doc_number,
        effective_date=effective_date,
        issued_date=issued_date,
    )


def _relation(
    source: UUID, target: UUID, relation_type: RelationType, rel_id: UUID | None = None
) -> DocumentRelation:
    return DocumentRelation(
        id=rel_id or uuid.uuid4(),
        source_doc_id=source,
        target_doc_id=target,
        relation_type=relation_type,
    )


def _chunk(
    doc_id: UUID,
    *,
    chunk_id: UUID | None = None,
    content: str = "nội dung",
    score: float = 0.5,
    section_title: str | None = None,
    section_number: str | None = None,
    chunk_index: int = 0,
    page_number: int | None = None,
    metadata: dict | None = None,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=doc_id,
        content=content,
        score=score,
        retrieval_method="hybrid",
        section_title=section_title,
        section_number=section_number,
        chunk_index=chunk_index,
        page_number=page_number,
        metadata=metadata if metadata is not None else {},
    )


def _context(
    *,
    ranked_chunks: list[SearchResult] | None = None,
    document_map: dict[UUID, Document] | None = None,
    relationships: list[DocumentRelation] | None = None,
) -> KnowledgeContext:
    chunks = ranked_chunks or []
    return KnowledgeContext(
        query="test query",
        retrieved_chunks=chunks,
        ranked_chunks=chunks,
        document_map=document_map or {},
        relationships=relationships or [],
    )


# ===========================================================================
# 1. Authority Ranking (AuthorityRankingProcessor)
# ===========================================================================


class TestAuthorityRanking:
    @pytest.mark.asyncio
    async def test_higher_authority_ranks_first_when_raw_scores_tie(self):
        """Văn bản Luật (NATIONAL_LAW, score=1.0) phải được ưu tiên hơn văn bản
        SOP nội bộ (DEPARTMENT_SOP, score=0.3) khi điểm retrieval ban đầu bằng nhau."""
        doc_law = _document(_DOC_A, authority_level=AuthorityLevel.NATIONAL_LAW)
        doc_sop = _document(_DOC_B, authority_level=AuthorityLevel.DEPARTMENT_SOP)
        chunk_sop = _chunk(_DOC_B, score=0.6)
        chunk_law = _chunk(_DOC_A, score=0.6)
        context = _context(
            ranked_chunks=[chunk_sop, chunk_law],  # SOP nhập trước để test có sort lại
            document_map={_DOC_A: doc_law, _DOC_B: doc_sop},
        )

        await AuthorityRankingProcessor(authority_weight=0.5).process(context)

        assert context.ranked_chunks[0].document_id == _DOC_A
        assert context.ranked_chunks[0].score > context.ranked_chunks[1].score

    @pytest.mark.asyncio
    async def test_score_blend_formula_is_exact(self):
        """score' = (1 - weight) * score + weight * authority_score — kiểm tra đúng công thức."""
        doc = _document(_DOC_A, authority_level=AuthorityLevel.NHNN_CIRCULAR)  # 0.8
        chunk = _chunk(_DOC_A, score=0.6)
        context = _context(ranked_chunks=[chunk], document_map={_DOC_A: doc})

        await AuthorityRankingProcessor(authority_weight=0.25).process(context)

        expected = 0.75 * 0.6 + 0.25 * 0.8
        assert context.ranked_chunks[0].score == pytest.approx(expected)
        assert context.ranked_chunks[0].metadata["authority_score"] == pytest.approx(0.8)
        assert context.ranked_chunks[0].metadata["authority_level"] == "NHNN_CIRCULAR"

    @pytest.mark.asyncio
    async def test_chunk_with_no_matching_document_gets_zero_authority(self):
        """Chunk có document_id không có trong document_map -> authority_score=0.0,
        không crash, không gắn field authority_level."""
        chunk = _chunk(_DOC_A, score=0.9)
        context = _context(ranked_chunks=[chunk], document_map={})

        await AuthorityRankingProcessor(authority_weight=0.5).process(context)

        assert context.ranked_chunks[0].metadata["authority_score"] == 0.0
        assert "authority_level" not in context.ranked_chunks[0].metadata
        assert context.ranked_chunks[0].score == pytest.approx(0.45)  # 0.5*0.9 + 0.5*0

    @pytest.mark.asyncio
    async def test_custom_authority_scores_override_default(self):
        """Cho phép truyền bảng điểm authority tùy chỉnh thay vì mặc định."""
        doc = _document(_DOC_A, authority_level=AuthorityLevel.FAQ)
        chunk = _chunk(_DOC_A, score=0.5)
        context = _context(ranked_chunks=[chunk], document_map={_DOC_A: doc})

        processor = AuthorityRankingProcessor(
            authority_scores={"FAQ": 0.99}, authority_weight=1.0
        )
        await processor.process(context)

        assert context.ranked_chunks[0].score == pytest.approx(0.99)

    @pytest.mark.asyncio
    async def test_sets_statistics_flag(self):
        context = _context(ranked_chunks=[_chunk(_DOC_A)], document_map={})
        await AuthorityRankingProcessor().process(context)
        assert context.statistics["authority_ranking_applied"] is True


# ===========================================================================
# 2. Relationship Expansion (RelationshipExpansionProcessor)
# ===========================================================================


class TestRelationshipExpansion:
    """`_fetch_relations`/`_fetch_documents` được monkeypatch thẳng (thay vì mock
    AsyncSession/SQLAlchemy) để test tập trung vào logic frontier/depth/cap —
    đây là phần có giá trị test thật, còn 2 hàm đó chỉ là SELECT thuần."""

    def _processor_with_fake_db(
        self,
        all_relations: list[DocumentRelation],
        all_docs: dict[UUID, Document],
        max_depth: int = 2,
        max_relations: int = 20,
    ) -> RelationshipExpansionProcessor:
        processor = RelationshipExpansionProcessor(
            session=AsyncMock(), max_depth=max_depth, max_relations=max_relations
        )

        async def fake_fetch_relations(doc_ids: list[UUID]) -> list[DocumentRelation]:
            ids = set(doc_ids)
            return [
                r
                for r in all_relations
                if r.source_doc_id in ids or r.target_doc_id in ids
            ]

        async def fake_fetch_documents(doc_ids: list[UUID]) -> dict[UUID, Document]:
            return {did: all_docs[did] for did in doc_ids if did in all_docs}

        processor._fetch_relations = fake_fetch_relations  # type: ignore[method-assign]
        processor._fetch_documents = fake_fetch_documents  # type: ignore[method-assign]
        return processor

    @pytest.mark.asyncio
    async def test_expands_to_related_document_not_in_top_k(self):
        """A được retrieve trực tiếp; B chỉ liên quan qua quan hệ AMENDS ->
        RelationshipExpansionProcessor phải tự kéo B vào document_map dù B
        không nằm trong top-k retrieval ban đầu."""
        rel_ab = _relation(_DOC_A, _DOC_B, RelationType.AMENDS)
        docs = {_DOC_A: _document(_DOC_A), _DOC_B: _document(_DOC_B)}
        context = _context(
            ranked_chunks=[_chunk(_DOC_A)],
            document_map={_DOC_A: docs[_DOC_A]},
            relationships=[rel_ab],
        )
        processor = self._processor_with_fake_db([rel_ab], docs)

        await processor.process(context)

        assert _DOC_B in context.document_map

    @pytest.mark.asyncio
    async def test_multi_hop_expansion_within_max_depth(self):
        """Chuỗi quan hệ A->B->C->D. A->B là hop "miễn phí" (tìm ngay từ
        relationships ban đầu); mỗi vòng lặp depth mở thêm đúng 1 hop nữa qua
        quan hệ của frontier hiện tại. max_depth=1 -> chỉ chạy 1 vòng, kéo
        được tới C (qua quan hệ của B) nhưng KHÔNG tới D (cần thêm 1 vòng nữa
        để duyệt quan hệ của C)."""
        rel_ab = _relation(_DOC_A, _DOC_B, RelationType.REFERENCES)
        rel_bc = _relation(_DOC_B, _DOC_C, RelationType.REFERENCES)
        rel_cd = _relation(_DOC_C, _DOC_D, RelationType.REFERENCES)
        docs = {d: _document(d) for d in (_DOC_A, _DOC_B, _DOC_C, _DOC_D)}
        context = _context(
            ranked_chunks=[_chunk(_DOC_A)],
            document_map={_DOC_A: docs[_DOC_A]},
            relationships=[rel_ab],
        )
        processor = self._processor_with_fake_db(
            [rel_ab, rel_bc, rel_cd], docs, max_depth=1
        )

        await processor.process(context)

        assert _DOC_C in context.document_map
        assert _DOC_D not in context.document_map

    @pytest.mark.asyncio
    async def test_max_relations_cap_stops_expansion(self):
        """max_relations đã đạt ngưỡng ngay từ đầu -> vòng lặp mở rộng dừng
        ngay, không fetch thêm quan hệ/document nào."""
        rel_ab = _relation(_DOC_A, _DOC_B, RelationType.AMENDS)
        docs = {_DOC_A: _document(_DOC_A), _DOC_B: _document(_DOC_B)}
        context = _context(
            ranked_chunks=[_chunk(_DOC_A)],
            document_map={_DOC_A: docs[_DOC_A]},
            relationships=[rel_ab],
        )
        processor = self._processor_with_fake_db([rel_ab], docs, max_relations=1)

        await processor.process(context)

        # B vẫn được thêm ở bước "initial frontier" (trước vòng lặp, không bị
        # cap), nhưng relationships không tăng thêm vì đã chạm max_relations=1
        # ngay từ đầu vòng lặp mở rộng theo depth.
        assert _DOC_B in context.document_map
        assert context.statistics["expansion_count"] == 0

    @pytest.mark.asyncio
    async def test_no_relationships_means_no_expansion(self):
        context = _context(
            ranked_chunks=[_chunk(_DOC_A)],
            document_map={_DOC_A: _document(_DOC_A)},
            relationships=[],
        )
        processor = self._processor_with_fake_db([], {})

        await processor.process(context)

        assert list(context.document_map.keys()) == [_DOC_A]
        assert context.statistics["expansion_count"] == 0


# ===========================================================================
# 3. Version Resolver (VersionResolutionProcessor)
# ===========================================================================


class TestVersionResolver:
    @pytest.mark.asyncio
    async def test_chunk_from_superseded_document_is_penalized(self):
        """Doc cũ (target của REPLACES) bị đánh dấu superseded và giảm điểm
        theo `superseded_penalty`."""
        rel = _relation(_DOC_B, _DOC_A, RelationType.REPLACES)  # B thay thế A
        chunk_a = _chunk(_DOC_A, score=0.8)
        context = _context(
            ranked_chunks=[chunk_a],
            document_map={_DOC_A: _document(_DOC_A)},
            relationships=[rel],
        )

        await VersionResolutionProcessor(superseded_penalty=0.5).process(context)

        assert chunk_a.metadata["superseded"] is True
        assert chunk_a.metadata["version_note"] == "Đã bị thay thế bởi văn bản mới hơn"
        assert chunk_a.score == pytest.approx(0.4)

    @pytest.mark.asyncio
    async def test_chunk_from_current_document_is_untouched(self):
        rel = _relation(_DOC_B, _DOC_A, RelationType.REPLACES)
        chunk_b = _chunk(_DOC_B, score=0.7)
        context = _context(
            ranked_chunks=[chunk_b],
            document_map={_DOC_B: _document(_DOC_B)},
            relationships=[rel],
        )

        await VersionResolutionProcessor().process(context)

        assert chunk_b.metadata["superseded"] is False
        assert chunk_b.score == pytest.approx(0.7)

    @pytest.mark.asyncio
    async def test_resorts_after_penalty_changes_order(self):
        rel = _relation(_DOC_B, _DOC_A, RelationType.REPLACES)
        chunk_a = _chunk(_DOC_A, score=0.9)  # sẽ bị phạt xuống 0.45
        chunk_b = _chunk(_DOC_B, score=0.5)  # không bị phạt
        context = _context(
            ranked_chunks=[chunk_a, chunk_b],
            document_map={_DOC_A: _document(_DOC_A), _DOC_B: _document(_DOC_B)},
            relationships=[rel],
        )

        await VersionResolutionProcessor(superseded_penalty=0.5).process(context)

        assert context.ranked_chunks[0].document_id == _DOC_B

    @pytest.mark.asyncio
    async def test_superseded_count_statistic(self):
        rel1 = _relation(_DOC_B, _DOC_A, RelationType.REPLACES)
        rel2 = _relation(_DOC_D, _DOC_C, RelationType.REPLACES)
        context = _context(relationships=[rel1, rel2])

        await VersionResolutionProcessor().process(context)

        assert context.statistics["superseded_count"] == 2

    @pytest.mark.asyncio
    async def test_version_note_added_to_context_metadata(self):
        rel = _relation(_DOC_B, _DOC_A, RelationType.REPLACES)
        doc_a = _document(_DOC_A, title="Luật cũ 2018")
        chunk_a = _chunk(_DOC_A)
        context = _context(
            ranked_chunks=[chunk_a],
            document_map={_DOC_A: doc_a},
            relationships=[rel],
        )

        await VersionResolutionProcessor().process(context)

        assert "Luật cũ 2018 đã bị thay thế" in context.metadata["version_notes"]


# ===========================================================================
# 4. Amendment Resolver (DocumentRelationService.apply_amendment)
# ===========================================================================
# Bổ sung thêm case cho apply_amendment (case cơ bản đã có ở
# test_document_relation.py) — tập trung vào tie-break và input rỗng.


class TestAmendmentResolver:
    def _service(self) -> DocumentRelationService:
        return DocumentRelationService(session=AsyncMock())

    def test_empty_input_returns_empty(self):
        assert self._service().apply_amendment([]) == []

    def test_three_chunks_same_document_keeps_only_max_score(self):
        service = self._service()
        c1 = _chunk(_DOC_A, score=0.2)
        c2 = _chunk(_DOC_A, score=0.9)
        c3 = _chunk(_DOC_A, score=0.5)

        kept = service.apply_amendment([c1, c2, c3])

        assert len(kept) == 1
        assert kept[0].score == 0.9

    def test_tie_break_keeps_first_seen_chunk(self):
        """Khi 2 chunk cùng document có score bằng nhau, giữ chunk gặp trước
        (do điều kiện so sánh dùng `>` chứ không phải `>=`)."""
        service = self._service()
        first = _chunk(_DOC_A, score=0.5, chunk_id=UUID(int=1))
        second = _chunk(_DOC_A, score=0.5, chunk_id=UUID(int=2))

        kept = service.apply_amendment([first, second])

        assert len(kept) == 1
        assert kept[0].chunk_id == first.chunk_id


# ===========================================================================
# 5. Conflict Detection (ConflictDetectionProcessor — bản wired vào pipeline)
# ===========================================================================


class TestConflictDetection:
    @pytest.mark.asyncio
    async def test_disabled_processor_reports_zero_and_skips(self):
        context = _context(ranked_chunks=[_chunk(_DOC_A)])
        context.conflicts = ["sentinel"]  # type: ignore[list-item]

        await ConflictDetectionProcessor(enabled=False).process(context)

        assert context.statistics["conflict_count"] == 0
        assert context.conflicts == ["sentinel"]  # không bị processor đụng vào

    @pytest.mark.asyncio
    async def test_flags_conflict_when_related_doc_is_retrieved(self):
        rel = _relation(_DOC_A, _DOC_B, RelationType.CONFLICTS_WITH)
        context = _context(
            ranked_chunks=[_chunk(_DOC_A)],
            document_map={
                _DOC_A: _document(_DOC_A, title="Thông tư 48/2018"),
                _DOC_B: _document(_DOC_B, title="Thông tư 49/2018"),
            },
            relationships=[rel],
        )

        await ConflictDetectionProcessor().process(context)

        assert len(context.conflicts) == 1
        assert context.conflicts[0].source_doc_id == _DOC_A
        assert context.metadata["has_conflicts"] is True

    @pytest.mark.asyncio
    async def test_no_conflict_when_neither_document_retrieved(self):
        """Quan hệ CONFLICTS_WITH tồn tại nhưng không liên quan gì tới các
        chunk đang được trả lời -> không nên báo conflict giả."""
        rel = _relation(_DOC_C, _DOC_D, RelationType.CONFLICTS_WITH)
        context = _context(
            ranked_chunks=[_chunk(_DOC_A)],
            document_map={_DOC_A: _document(_DOC_A)},
            relationships=[rel],
        )

        await ConflictDetectionProcessor().process(context)

        assert context.conflicts == []
        assert "has_conflicts" not in context.metadata

    @pytest.mark.asyncio
    async def test_non_conflict_relation_types_are_ignored(self):
        rel = _relation(_DOC_A, _DOC_B, RelationType.AMENDS)
        context = _context(
            ranked_chunks=[_chunk(_DOC_A)],
            document_map={_DOC_A: _document(_DOC_A), _DOC_B: _document(_DOC_B)},
            relationships=[rel],
        )

        await ConflictDetectionProcessor().process(context)

        assert context.conflicts == []


# ===========================================================================
# 6. Citation Builder (CitationProcessor)
# ===========================================================================


class TestCitationBuilder:
    @pytest.mark.asyncio
    async def test_builds_citation_with_correct_fields(self):
        doc = _document(
            _DOC_A,
            authority_level=AuthorityLevel.NHNN_CIRCULAR,
            doc_number="48/2018/TT-NHNN",
            version=2,
            effective_date=date(2019, 7, 5),
        )
        chunk = _chunk(
            _DOC_A,
            section_title="Điều 3.",
            section_number="Khoản 2",
            chunk_index=5,
            content="Công dân Việt Nam từ đủ 15 tuổi đến chưa đủ 18 tuổi...",
        )
        context = _context(ranked_chunks=[chunk], document_map={_DOC_A: doc})

        await CitationProcessor().process(context)

        cit = context.citations[0]
        assert cit.document_title == doc.title
        assert cit.doc_number == "48/2018/TT-NHNN"
        assert cit.section_number == "Khoản 2"
        assert cit.section_title == "Điều 3."
        assert cit.authority_level == "NHNN_CIRCULAR"
        assert cit.version == 2
        assert cit.effective_date == date(2019, 7, 5)
        assert cit.chunk_index == 5

    @pytest.mark.asyncio
    async def test_respects_max_citations_cap(self):
        chunks = [_chunk(_DOC_A, chunk_index=i) for i in range(5)]
        context = _context(ranked_chunks=chunks, document_map={_DOC_A: _document(_DOC_A)})

        await CitationProcessor(max_citations=2).process(context)

        assert len(context.citations) == 2
        assert context.statistics["citation_count"] == 2

    @pytest.mark.asyncio
    async def test_content_preview_truncated_to_200_chars(self):
        long_content = "x" * 500
        chunk = _chunk(_DOC_A, content=long_content)
        context = _context(ranked_chunks=[chunk], document_map={_DOC_A: _document(_DOC_A)})

        await CitationProcessor().process(context)

        assert len(context.citations[0].content_preview) == 200

    @pytest.mark.asyncio
    async def test_missing_document_falls_back_to_defaults(self):
        chunk = _chunk(_DOC_A)
        context = _context(ranked_chunks=[chunk], document_map={})

        await CitationProcessor().process(context)

        cit = context.citations[0]
        assert cit.document_title == "Unknown"
        assert cit.doc_number is None
        assert cit.authority_level == "UNKNOWN"
        assert cit.version == 1
        assert cit.effective_date is None

    @pytest.mark.asyncio
    async def test_disabled_processor_does_not_touch_citations(self):
        context = _context(ranked_chunks=[_chunk(_DOC_A)], document_map={_DOC_A: _document(_DOC_A)})
        context.citations = ["sentinel"]  # type: ignore[list-item]

        await CitationProcessor(enabled=False).process(context)

        assert context.citations == ["sentinel"]


# ===========================================================================
# 7. Timeline Builder (TimelineProcessor)
# ===========================================================================


class TestTimelineBuilder:
    @pytest.mark.asyncio
    async def test_builds_oldest_to_current_chain(self):
        """Chuỗi V1 -REPLACES-> V2 -REPLACES-> V3 (V2 thay thế V1, V3 thay
        thế V2) phải cho ra timeline theo thứ tự V1 (cũ nhất) -> V3 (hiện tại)."""
        rel_v2_replaces_v1 = _relation(_DOC_B, _DOC_A, RelationType.REPLACES)
        rel_v3_replaces_v2 = _relation(_DOC_C, _DOC_B, RelationType.REPLACES)
        docs = {
            _DOC_A: _document(_DOC_A, title="Luật V1", version=1),
            _DOC_B: _document(_DOC_B, title="Luật V2", version=2),
            _DOC_C: _document(_DOC_C, title="Luật V3", version=3),
        }
        context = _context(
            document_map=docs,
            relationships=[rel_v2_replaces_v1, rel_v3_replaces_v2],
        )

        await TimelineProcessor().process(context)

        titles = [e.document_title for e in context.timeline]
        assert titles == ["Luật V1", "Luật V2", "Luật V3"]
        assert context.timeline[0].is_current is False
        assert context.timeline[1].is_current is False
        assert context.timeline[-1].is_current is True
        assert context.statistics["timeline_entries"] == 3

    @pytest.mark.asyncio
    async def test_no_replaces_relations_gives_empty_timeline(self):
        context = _context(relationships=[_relation(_DOC_A, _DOC_B, RelationType.AMENDS)])

        await TimelineProcessor().process(context)

        assert context.timeline == []

    @pytest.mark.asyncio
    async def test_disabled_processor_does_not_build_timeline(self):
        rel = _relation(_DOC_B, _DOC_A, RelationType.REPLACES)
        context = _context(relationships=[rel])

        await TimelineProcessor(enabled=False).process(context)

        assert context.timeline == []

    @pytest.mark.asyncio
    async def test_circular_replaces_relation_does_not_crash(self):
        """A thay thế B và B thay thế A (dữ liệu mâu thuẫn/lỗi) -> không tìm
        được điểm bắt đầu hợp lệ, timeline giữ nguyên rỗng, không raise."""
        rel_a_replaces_b = _relation(_DOC_A, _DOC_B, RelationType.REPLACES)
        rel_b_replaces_a = _relation(_DOC_B, _DOC_A, RelationType.REPLACES)
        context = _context(relationships=[rel_a_replaces_b, rel_b_replaces_a])

        await TimelineProcessor().process(context)

        assert context.timeline == []

    @pytest.mark.asyncio
    async def test_missing_document_falls_back_to_id_string(self):
        rel = _relation(_DOC_B, _DOC_A, RelationType.REPLACES)
        context = _context(document_map={}, relationships=[rel])

        await TimelineProcessor().process(context)

        assert context.timeline[0].document_title == str(_DOC_A)
