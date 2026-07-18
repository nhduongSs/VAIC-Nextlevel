from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.models.schemas import RetrievedChunk
from app.repositories.vector_store import get_vector_store

settings = get_settings()


class RAGService:
    def __init__(self):
        self._store = get_vector_store()
        self._embedder = SentenceTransformer(settings.embedding_model)

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        embedding = self._embedder.encode(query).tolist()
        return self._store.query(embedding)

    @staticmethod
    def build_context_block(chunks: list[RetrievedChunk]) -> str:
        """Định dạng context kèm nguồn để LLM có thể trích dẫn, tăng độ tin cậy."""
        parts = []
        for i, c in enumerate(chunks, 1):
            parts.append(f"[Nguồn {i}: {c.title} - {c.clause} - hiệu lực từ {c.effective_date}]\n{c.content}")
        return "\n\n".join(parts)
