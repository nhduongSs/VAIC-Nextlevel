import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.infrastructure.database.base import Base


class ChunkModel(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    section_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    chunk_type: Mapped[str] = mapped_column(String(30), nullable=False, default="PARAGRAPH")
    token_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    embedding: Mapped[Any] = mapped_column(Vector(1024), nullable=True)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    metadata_extra: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_chunks_document_id", "document_id"),
        Index("idx_chunks_document_index", "document_id", "chunk_index"),
        Index("idx_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "idx_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "idx_chunks_chunk_type",
            "chunk_type",
            postgresql_where=text("embedding IS NULL"),
        ),
    )
