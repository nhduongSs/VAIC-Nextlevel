"""
RAG core — Việc 5-8 (brief mục 3), phần ăn điểm nhất của đề bài:
amendment, partial supersession, cross-reference, conflict detection.
"""
from itertools import combinations

from app.models.schemas import ConflictInfo, DocStatus, RetrievedChunk
from app.repositories.relation_store import get_relation_store
from app.repositories.vector_store import get_vector_store


class DocumentRelationService:
    def __init__(self):
        self._relations = get_relation_store()
        self._store = get_vector_store()

    def apply_amendment(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Việc 5 — nếu nhiều chunk cùng chủ đề (title) khác effective_date,
        chỉ giữ bản có hiệu lực mới nhất."""
        latest_by_title: dict[str, RetrievedChunk] = {}
        for c in chunks:
            current = latest_by_title.get(c.title)
            if current is None or c.effective_date > current.effective_date:
                latest_by_title[c.title] = c
        return list(latest_by_title.values())

    def apply_partial_supersession(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Việc 6 — loại đúng phần điều khoản đã bị thay thế, giữ phần còn hiệu lực."""
        result = []
        for c in chunks:
            if c.status == DocStatus.HET_HIEU_LUC:
                continue
            if c.status == DocStatus.MOT_PHAN_HET_HIEU_LUC:
                superseded = self._relations.get_superseded_clauses(c.doc_id)
                if c.clause in superseded:
                    continue
            result.append(c)
        return result

    def apply_cross_reference(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Việc 7 — mở rộng lấy thêm chunk liên quan qua bảng quan hệ văn bản."""
        expanded = list(chunks)
        seen = {(c.doc_id, c.clause) for c in chunks}

        for c in chunks:
            for related_doc_id in self._relations.get_related_doc_ids(c.doc_id):
                related_chunks = self._store.query_by_doc_id(related_doc_id)
                for rc in related_chunks:
                    key = (rc.doc_id, rc.clause)
                    if key not in seen:
                        seen.add(key)
                        expanded.append(rc)
        return expanded

    def detect_conflicts(self, chunks: list[RetrievedChunk]) -> list[ConflictInfo]:
        """Việc 8 — so sánh nội dung các chunk còn hiệu lực, phát hiện mâu thuẫn.
        MVP: so sánh cặp chunk cùng chủ đề (title khác nhau) có nội dung số liệu
        (vd lãi suất) khác nhau -> cảnh báo, để LLM diễn giải chi tiết hơn ở bước generation."""
        conflicts: list[ConflictInfo] = []
        for a, b in combinations(chunks, 2):
            if a.doc_id == b.doc_id:
                continue
            if _same_topic(a, b) and _content_conflicts(a, b):
                conflicts.append(
                    ConflictInfo(
                        description=(
                            f"'{a.title}' ({a.clause}) và '{b.title}' ({b.clause}) "
                            "có nội dung khác nhau về cùng chủ đề."
                        ),
                        conflicting_sources=[a.doc_id, b.doc_id],
                    )
                )
        return conflicts


def _same_topic(a: RetrievedChunk, b: RetrievedChunk) -> bool:
    return a.clause.split(".")[0] == b.clause.split(".")[0] or a.title == b.title


def _content_conflicts(a: RetrievedChunk, b: RetrievedChunk) -> bool:
    return a.content.strip() != b.content.strip()
