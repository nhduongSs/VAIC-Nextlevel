"""
Bảng quan hệ văn bản (cross-reference, văn bản sửa đổi/thay thế) — Huy thu thập,
lưu chung trong Supabase Postgres, join với bảng vector (TechStack mục Vector DB).

Bảng gợi ý (Postgres):
  document_relations(
    id, source_doc_id, related_doc_id,
    relation_type,  -- 'cross_reference' | 'amends' | 'supersedes'
    superseded_clause  -- clause bị thay thế, null nếu là cross_reference
  )
"""

from app.core.config import get_settings

try:
    from supabase import Client, create_client
except ImportError:  # cho phép chạy test mà chưa cài supabase
    Client = None
    create_client = None

settings = get_settings()


class RelationStore:
    def __init__(self):
        self._client: Client | None = (
            create_client(settings.supabase_url, settings.supabase_key)
            if create_client and settings.supabase_url
            else None
        )

    def get_related_doc_ids(self, doc_id: str) -> list[str]:
        if not self._client:
            return []
        res = (
            self._client.table("document_relations")
            .select("related_doc_id")
            .eq("source_doc_id", doc_id)
            .eq("relation_type", "cross_reference")
            .execute()
        )
        return [row["related_doc_id"] for row in res.data]

    def get_superseded_clauses(self, doc_id: str) -> set[str]:
        if not self._client:
            return set()
        res = (
            self._client.table("document_relations")
            .select("superseded_clause")
            .eq("related_doc_id", doc_id)
            .eq("relation_type", "supersedes")
            .execute()
        )
        return {row["superseded_clause"] for row in res.data if row["superseded_clause"]}


_relation_store_instance: RelationStore | None = None


def get_relation_store() -> RelationStore:
    global _relation_store_instance
    if _relation_store_instance is None:
        _relation_store_instance = RelationStore()
    return _relation_store_instance
