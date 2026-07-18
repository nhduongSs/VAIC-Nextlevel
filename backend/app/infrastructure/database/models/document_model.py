import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, Index, Integer, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.infrastructure.database.base import Base


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    authority_level: Mapped[str] = mapped_column(String(50), nullable=False)
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expired_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="UPLOADED")
    issuing_body: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # File management fields
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Version tracking
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Flexible metadata
    tags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    metadata_extra: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Full-text search (populated by trigger in later wave)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "idx_documents_doc_type",
            "doc_type",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_documents_authority_level",
            "authority_level",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_documents_issued_date",
            "issued_date",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_documents_status",
            "status",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_documents_doc_number",
            "doc_number",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("idx_documents_content_hash", "content_hash"),
        Index("idx_documents_search_vector", "search_vector", postgresql_using="gin"),
        Index("idx_documents_tags", "tags", postgresql_using="gin"),
    )
