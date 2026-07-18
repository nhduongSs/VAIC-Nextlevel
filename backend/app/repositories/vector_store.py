"""
Vector store layer — bọc Supabase/pgvector để RAG service không phụ thuộc
trực tiếp vào 1 thư viện cụ thể. Gộp vector + metadata (ngày hiệu lực,
trạng thái) trong 1 bảng Postgres, lọc bằng SQL WHERE kết hợp vector search
trong 1 query (TechStack mục Vector DB).
"""
from app.core.config import get_settings
from app.models.schemas import DocStatus, RetrievedChunk
from app.repositories.document_loader import Clause

try:
    from supabase import Client, create_client
except ImportError:  # cho phép chạy test mà chưa cài supabase
    Client = None
    create_client = None

settings = get_settings()


class VectorStore:
    def __init__(self):
        self._client: "Client | None" = (
            create_client(settings.supabase_url, settings.supabase_key)
            if create_client and settings.supabase_url
            else None
        )

    def add_clauses(self, clauses: list[Clause], embeddings: list[list[float]]):
        if not self._client:
            return
        rows = [
            {
                "doc_id": c.doc_id,
                "title": c.title,
                "clause": c.clause,
                "effective_date": c.effective_date,
                "status": c.status,
                "content": c.content,
                "embedding": emb,
            }
            for c, emb in zip(clauses, embeddings)
        ]
        self._client.table("document_chunks").insert(rows).execute()

    def query(self, query_embedding: list[float], top_k: int | None = None) -> list[RetrievedChunk]:
        """Gọi RPC `match_document_chunks` (Postgres function) làm vector search +
        lọc status != 'het_hieu_luc' trong cùng 1 query."""
        top_k = top_k or settings.top_k_retrieval
        if not self._client:
            return []

        res = self._client.rpc(
            "match_document_chunks",
            {"query_embedding": query_embedding, "match_count": top_k},
        ).execute()

        return [
            RetrievedChunk(
                content=row["content"],
                doc_id=row["doc_id"],
                title=row["title"],
                clause=row["clause"],
                effective_date=row["effective_date"],
                status=DocStatus(row["status"]),
                score=row["similarity"],
            )
            for row in res.data
        ]

    def query_by_doc_id(self, doc_id: str) -> list[RetrievedChunk]:
        """Lấy toàn bộ chunk của 1 văn bản liên quan (dùng cho cross-reference),
        không qua vector search vì đã biết chính xác doc_id."""
        if not self._client:
            return []

        res = self._client.table("document_chunks").select("*").eq("doc_id", doc_id).execute()

        return [
            RetrievedChunk(
                content=row["content"],
                doc_id=row["doc_id"],
                title=row["title"],
                clause=row["clause"],
                effective_date=row["effective_date"],
                status=DocStatus(row["status"]),
                score=1.0,
            )
            for row in res.data
        ]


_store_instance: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = VectorStore()
    return _store_instance
