"""Nạp T&C / mô tả sản phẩm / biểu phí của các ngân hàng (`data/discovery/bank_docs/`)
vào schema Alembic live như Document/Chunk THƯỜNG — không cột SQL mới (đúng đề
xuất 2.4 của doc/Ontology_Implementation_Proposal.md): `doc_class="van_ban_noi_bo"`,
`bank=<Bank>` trong `metadata_extra`, tái dùng nguyên `MetadataFilter`/`Source`
ontology đã có sẵn cho corpus pháp lý.

Chạy: cd backend && python -m scripts.ingest_bank_docs
Cần: DB Postgres + embedding-service đang chạy (giống scripts/ingest.py).

Techcombank bị loại khỏi scope (đã chốt với user) — bỏ qua toàn bộ thư mục.

Theo `file_type` trong mỗi `manifest.json`:
- "markdown_summary" -> đọc thẳng nội dung .md
- "pdf" -> PdfParser (pymupdf, xem app/infrastructure/ingestion/parsers/pdf_parser.py)
  lấy raw_text, rồi HierarchicalChunker (tự nhận diện "Điều N" nếu có, fallback
  chunk 2000 ký tự nếu không)
- "json" -> bỏ qua (số liệu lãi suất, đã xử lý ở scripts/ingest_bank_rates.py)
- "none" -> case SHB không công bố lãi suất KHDN công khai: tổng hợp 1 Document
  ngắn từ field "notes" để chatbot trả lời đúng "liên hệ chi nhánh/Internet
  Banking doanh nghiệp" thay vì bịa số

Idempotent: giống scripts/ingest.py — xóa document cũ theo content_hash trước
khi nạp lại.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import structlog
from sqlalchemy import delete

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.core.logging import configure_logging
from app.infrastructure.ingestion.chunkers.hierarchical_chunker import (
    HierarchicalChunker,
)
from app.infrastructure.ingestion.parsed_document import ParsedDocument
from app.infrastructure.ingestion.parsers.pdf_parser import PdfParser
from app.models.entities import Document
from app.models.enums import AuthorityLevel, DocumentStatus, DocumentType
from app.models.orm import DocumentModel
from app.repositories.document_store import PgChunkRepository, PgDocumentRepository
from app.services.embedding_service import EmbeddingService
from app.repositories.vector_store import EmbeddingClient

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
BANK_DOCS_DIR = REPO_ROOT / "data" / "discovery" / "bank_docs"
_SKIP_BANK_DIRS = {"techcombank"}

_pdf_parser = PdfParser()
_chunker = HierarchicalChunker()


_CRAWL_ARTIFACT_KEYWORDS = ("không tải được", "sharepoint", "lỗi khi tải")


def _is_crawl_artifact(entry: dict[str, object]) -> bool:
    """Phân biệt entry `file_type=none` là ghi chú nghiệp vụ thật (vd case SHB
    không công bố lãi suất KHDN công khai — nên ingest) với ghi chú lỗi crawl
    (vd VCB: link tải hỏng, đã dùng PDF khác thay thế — nội dung thật đã nằm ở
    entry PDF khác trong cùng manifest, ingest lại đây chỉ tạo nhiễu)."""
    haystack = f"{entry.get('title', '')} {entry.get('notes', '')}".lower()
    return any(kw in haystack for kw in _CRAWL_ARTIFACT_KEYWORDS)


def _build_metadata_extra(entry: dict[str, object]) -> dict[str, object]:
    segment = entry.get("customer_segment")
    return {
        "doc_class": "van_ban_noi_bo",
        "legal_status": None,
        "bank": entry["bank"],
        "category": entry["category"],
        "doi_tuong_ap_dung": [segment] if segment else [],
    }


async def _load_raw_text(bank_dir: Path, entry: dict[str, object]) -> tuple[bytes, str, str]:
    """Return (raw_bytes_for_hash, content_type, raw_text)."""
    file_type = entry["file_type"]

    if file_type == "markdown_summary":
        path = bank_dir / entry["local_path"]
        raw_bytes = path.read_bytes()
        return raw_bytes, "text/markdown", raw_bytes.decode("utf-8")

    if file_type == "pdf":
        path = bank_dir / entry["local_path"]
        raw_bytes = path.read_bytes()
        parsed: ParsedDocument = await _pdf_parser.parse(raw_bytes, path.name)
        return raw_bytes, "application/pdf", parsed.raw_text

    if file_type == "none":
        text = str(entry.get("notes", "")).strip()
        raw_bytes = text.encode("utf-8")
        return raw_bytes, "text/markdown", text

    raise ValueError(f"unsupported file_type: {file_type}")


async def _ingest_entry(
    bank_dir: Path, entry: dict[str, object], embedding_service: EmbeddingService
) -> dict[str, object] | None:
    file_type = entry["file_type"]
    if file_type == "json":
        return None  # số liệu lãi suất — xử lý ở ingest_bank_rates.py
    if file_type == "none" and _is_crawl_artifact(entry):
        return None  # ghi chú lỗi crawl (vd "không tải được file"), không phải
        # nội dung nghiệp vụ thật — nội dung thay thế đã được ingest ở entry PDF khác

    raw_bytes, content_type, raw_text = await _load_raw_text(bank_dir, entry)
    if not raw_text.strip():
        log.warning("ingest_bank_docs_empty", bank=entry["bank"], title=entry["title"])
        return None

    local_path = entry.get("local_path")
    filename = Path(local_path).name if local_path else f"{entry['bank']}_gap_note.md"
    file_path = (
        f"data/discovery/bank_docs/{bank_dir.name}/{local_path}"
        if local_path
        else f"data/discovery/bank_docs/{bank_dir.name}/{filename}"
    )

    now = datetime.now(UTC)
    document_id = uuid.uuid4()
    metadata_extra = _build_metadata_extra(entry)

    document = Document(
        id=document_id,
        title=str(entry["title"]),
        filename=filename,
        original_filename=filename,
        content_type=content_type,
        file_size=len(raw_bytes),
        file_path=file_path,
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
        status=DocumentStatus.READY,
        version=1,
        doc_type=DocumentType.PRODUCT_DOC,
        authority_level=AuthorityLevel.INTERNAL_POLICY,
        created_at=now,
        updated_at=now,
        doc_number=None,
        effective_date=None,
        metadata_extra=dict(metadata_extra),
    )

    parsed = ParsedDocument(raw_text=raw_text)
    chunks = _chunker.chunk(document_id, parsed)
    for chunk in chunks:
        chunk.metadata_extra = dict(metadata_extra)

    async with AsyncSessionFactory() as session:
        doc_repo = PgDocumentRepository(session)
        chunk_repo = PgChunkRepository(session)

        existing = await doc_repo.get_by_checksum(document.content_hash)
        if existing is not None:
            await session.execute(
                delete(DocumentModel).where(DocumentModel.id == existing.id)
            )
            log.info(
                "ingest_bank_docs_replacing_existing",
                title=document.title,
                old_document_id=str(existing.id),
            )

        await doc_repo.create(document)
        await chunk_repo.bulk_insert(chunks)
        await session.commit()

    await embedding_service.embed_document(document.id)

    return {"bank": entry["bank"], "title": entry["title"], "chunks": len(chunks)}


async def main() -> None:
    if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    configure_logging(settings.LOG_LEVEL)

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
    for bank_dir in sorted(p for p in BANK_DOCS_DIR.iterdir() if p.is_dir()):
        if bank_dir.name in _SKIP_BANK_DIRS:
            print(f"  (bỏ qua {bank_dir.name} — ngoài scope)")
            continue

        manifest_path = bank_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))

        for entry in entries:
            result = await _ingest_entry(bank_dir, entry, embedding_service)
            if result is None:
                continue
            report.append(result)
            print(f"  {result['bank']:<12} {result['chunks']:>3} chunks  {result['title'][:60]}")

    by_bank: dict[str, int] = {}
    for r in report:
        by_bank[str(r["bank"])] = by_bank.get(str(r["bank"]), 0) + int(r["chunks"])

    print(f"\nĐã nạp {len(report)} document ({sum(by_bank.values())} chunks):")
    for bank, count in by_bank.items():
        print(f"  {bank:<12} {count} chunks")


if __name__ == "__main__":
    asyncio.run(main())
