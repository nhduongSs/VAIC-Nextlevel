"""Nạp corpus `data/raw/` vào schema Alembic live (documents/chunks, hybrid BM25+vector).

Chạy: cd backend && python -m scripts.ingest
Cần: DB Postgres ở DATABASE_URL (mặc định localhost:5434) và embedding-service ở
EMBEDDING_SERVICE_URL (mặc định docker hostname `embedding-service:8001` — đặt
EMBEDDING_SERVICE_URL=http://localhost:8001 trong .env nếu chạy script từ host).

Mỗi Điều trong data/raw/<category>/*.md (xem app/repositories/document_loader.py)
trở thành một Chunk; mỗi file trở thành một Document. Ý tưởng ontology (doc_class,
legal_status, category, doi_tuong_ap_dung) được lưu trong metadata_extra JSONB —
không có cột SQL mới, không dùng RPC Supabase (xem
doc/Corpus_Ingestion_Ontology_Plan.md).

Idempotent: nếu content_hash đã tồn tại (rerun), xóa document cũ (cascade chunks)
rồi nạp lại.
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import structlog
from sqlalchemy import delete

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.core.logging import configure_logging
from app.models.entities import Chunk, Document
from app.models.enums import AuthorityLevel, ChunkType, DocumentStatus, DocumentType
from app.models.orm import DocumentModel
from app.repositories import document_loader
from app.repositories.document_loader import Clause
from app.repositories.document_store import PgChunkRepository, PgDocumentRepository
from app.repositories.vector_store import EmbeddingClient
from app.services.embedding_service import EmbeddingService

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "raw"

# ── Ontology inference (Phase C của doc/Corpus_Ingestion_Ontology_Plan.md) ────

_DOC_CLASS_TO_TYPE: dict[str, tuple[DocumentType, AuthorityLevel]] = {
    "luat": (DocumentType.LAW, AuthorityLevel.NATIONAL_LAW),
    "phap_lenh": (DocumentType.LAW, AuthorityLevel.NATIONAL_LAW),
    "nghi_dinh": (DocumentType.DECREE, AuthorityLevel.UNKNOWN),
    "quyet_dinh": (DocumentType.DECISION, AuthorityLevel.NHNN_DECISION),
    "thong_tu": (DocumentType.CIRCULAR, AuthorityLevel.NHNN_CIRCULAR),
    "thong_tu_hop_nhat": (DocumentType.CIRCULAR, AuthorityLevel.NHNN_CIRCULAR),
}
_DEFAULT_DOC_TYPE = (DocumentType.UNKNOWN, AuthorityLevel.UNKNOWN)

_BOTH = ["ca_nhan", "doanh_nghiep"]
_CA_NHAN_ONLY = ["ca_nhan"]

# doi_tuong_ap_dung theo doc_id cụ thể (đã xác minh từ nội dung thật, xem plan).
_DOI_TUONG_BY_DOC_ID: dict[str, list[str]] = {
    "48/2018/TT-NHNN": _CA_NHAN_ONLY,
}
# Fallback theo category khi doc_id không có override riêng.
_DOI_TUONG_BY_CATEGORY: dict[str, list[str]] = {
    "bao_hiem": _CA_NHAN_ONLY,
    "lai_suat": _BOTH,
    "ngoai_hoi": _BOTH,
    "rut_truoc_han": _BOTH,
    "to_chuc_tin_dung": _BOTH,
}


def infer_doc_class(doc_id: str) -> str:
    """Ontology class (tiếng Việt, dùng để lọc) suy từ doc_id."""
    if "VBHN" in doc_id:
        return "thong_tu_hop_nhat"
    if "TT-" in doc_id:
        return "thong_tu"
    if "NĐ-CP" in doc_id or "ND-CP" in doc_id:
        return "nghi_dinh"
    if "QĐ-" in doc_id or "QD-" in doc_id:
        return "quyet_dinh"
    if "PL-" in doc_id:
        return "phap_lenh"
    if "QH" in doc_id:
        return "luat"
    return "cong_van"


def infer_doi_tuong(doc_id: str, category: str) -> list[str]:
    return _DOI_TUONG_BY_DOC_ID.get(
        doc_id, _DOI_TUONG_BY_CATEGORY.get(category, _BOTH)
    )


# ── Load corpus ────────────────────────────────────────────────────────────────


@dataclass
class LoadedDoc:
    doc_id: str
    title: str
    effective_date: str
    legal_status: str
    category: str
    filename: str
    file_path: Path
    raw_bytes: bytes
    clauses: list[Clause]


def load_corpus(data_dir: Path) -> list[LoadedDoc]:
    """Duyệt data/raw/<category>/*.md, parse mỗi file bằng document_loader."""
    docs: list[LoadedDoc] = []
    for category_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        for file_path in sorted(category_dir.glob("*.md")):
            raw_bytes = file_path.read_bytes()
            clauses = document_loader._parse_document(raw_bytes.decode("utf-8"))
            if not clauses:
                log.warning("ingest_skip_unparsed_file", path=str(file_path))
                continue
            first = clauses[0]
            docs.append(
                LoadedDoc(
                    doc_id=first.doc_id,
                    title=first.title,
                    effective_date=first.effective_date,
                    legal_status=first.status,
                    category=category_dir.name,
                    filename=file_path.name,
                    file_path=file_path,
                    raw_bytes=raw_bytes,
                    clauses=clauses,
                )
            )
    return docs


def build_document_and_chunks(doc: LoadedDoc) -> tuple[Document, list[Chunk]]:
    doc_class = infer_doc_class(doc.doc_id)
    doc_type, authority_level = _DOC_CLASS_TO_TYPE.get(doc_class, _DEFAULT_DOC_TYPE)
    metadata_extra = {
        "doc_class": doc_class,
        "legal_status": doc.legal_status,
        "category": doc.category,
        "doi_tuong_ap_dung": infer_doi_tuong(doc.doc_id, doc.category),
        "bank": None,
    }

    now = datetime.now(UTC)
    document_id = uuid.uuid4()
    document = Document(
        id=document_id,
        title=doc.title,
        filename=doc.filename,
        original_filename=doc.filename,
        content_type="text/markdown",
        file_size=len(doc.raw_bytes),
        file_path=doc.file_path.relative_to(REPO_ROOT).as_posix(),
        content_hash=hashlib.sha256(doc.raw_bytes).hexdigest(),
        status=DocumentStatus.READY,
        version=1,
        doc_type=doc_type,
        authority_level=authority_level,
        created_at=now,
        updated_at=now,
        doc_number=doc.doc_id,
        effective_date=date.fromisoformat(doc.effective_date),
        metadata_extra=dict(metadata_extra),
    )

    chunks = [
        Chunk(
            id=uuid.uuid4(),
            document_id=document_id,
            content=clause.content,
            chunk_index=idx,
            chunk_type=ChunkType.ARTICLE,
            section_title=clause.clause,
            token_count=len(clause.content) // 4,
            metadata_extra=dict(metadata_extra),
            created_at=now,
        )
        for idx, clause in enumerate(doc.clauses)
    ]
    return document, chunks


async def _ingest_one(
    doc: LoadedDoc, embedding_service: EmbeddingService
) -> dict[str, object]:
    document, chunks = build_document_and_chunks(doc)

    async with AsyncSessionFactory() as session:
        doc_repo = PgDocumentRepository(session)
        chunk_repo = PgChunkRepository(session)

        existing = await doc_repo.get_by_checksum(document.content_hash)
        if existing is not None:
            await session.execute(
                delete(DocumentModel).where(DocumentModel.id == existing.id)
            )
            log.info(
                "ingest_replacing_existing",
                doc_id=doc.doc_id,
                old_document_id=str(existing.id),
            )

        await doc_repo.create(document)
        await chunk_repo.bulk_insert(chunks)
        await session.commit()

    await embedding_service.embed_document(document.id)

    return {
        "doc_id": doc.doc_id,
        "clauses": len(chunks),
        "legal_status": doc.legal_status,
        "doc_class": document.metadata_extra["doc_class"],
    }


async def main() -> None:
    if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    configure_logging(settings.LOG_LEVEL)

    docs = load_corpus(DATA_DIR)
    if not docs:
        print(f"Không tìm thấy văn bản nào trong {DATA_DIR}. Kiểm tra lại đường dẫn/định dạng.")
        return

    embedding_client = EmbeddingClient(
        base_url=settings.EMBEDDING_SERVICE_URL,
        timeout=settings.EMBEDDING_TIMEOUT,
    )
    embedding_service = EmbeddingService(
        session_factory=AsyncSessionFactory,
        provider=embedding_client,
        batch_size=settings.EMBEDDING_BATCH_SIZE,
        max_concurrency=settings.EMBEDDING_MAX_CONCURRENCY,
        max_retries=settings.EMBEDDING_MAX_RETRIES,
        retry_delay=settings.EMBEDDING_RETRY_DELAY,
        batch_timeout=settings.EMBEDDING_BATCH_TIMEOUT,
    )

    report: list[dict[str, object]] = []
    for doc in docs:
        result = await _ingest_one(doc, embedding_service)
        report.append(result)
        print(
            f"  {result['doc_id']:<25} {result['clauses']:>3} Điều  "
            f"legal_status={result['legal_status']:<22} doc_class={result['doc_class']}"
        )

    total_clauses = sum(int(r["clauses"]) for r in report)
    print(f"\nĐã nạp {len(report)} văn bản, {total_clauses} Điều.")


if __name__ == "__main__":
    asyncio.run(main())
