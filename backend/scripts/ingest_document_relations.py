"""Nạp quan hệ văn bản pháp lý (`data/discovery/relations/**/*.json`, cào từ
tab "Lược đồ" trên vbpl.vn / API vbpl-bientap-gateway.moj.gov.vn) vào bảng
`document_relations`, ánh xạ sang 6 loại quan hệ đã có sẵn trong
`RelationType` (REPLACES/AMENDS/REFERENCES/SUPPLEMENTS/IMPLEMENTS/CONFLICTS_WITH)
— không thêm cột/enum value mới.

Chạy: cd backend && python -m scripts.ingest_document_relations
Cần: DB Postgres đang chạy, và corpus `data/raw/` đã được `scripts.ingest`
nạp trước đó (script này chỉ resolve theo `documents.doc_number` đã có sẵn
trong DB — không tự tạo document mới cho văn bản chưa ingest).

Cấu trúc 1 file quan hệ:
    {"doc_number": "48/2018/TT-NHNN", "relations": {
        "<raw_key>": {"label_vi": "...", "direction": "incoming|outgoing",
                       "documents": [{"doc_number": "...", "title": "..."}]}
    }}

Mỗi `raw_key` map sang 1 `RelationType` + hướng quan hệ (xem `_RELATION_MAP`).
`direction="outgoing"` nghĩa là "văn bản này -> văn bản trong list"
(source=chính nó, target=văn bản liệt kê); `"incoming"` thì ngược lại.

12 raw_key quan sát được trong dữ liệu thật (không phải file nào cũng có đủ
12 — 1 số file chỉ cào được quan hệ outgoing qua API, xem field "source" của
từng file):
  thay_the/bi_thay_the           -> REPLACES (thay thế / bị thay thế)
  sua_doi_bo_sung                -> AMENDS (sửa đổi, bổ sung)
  dinh_chinh/bi_dinh_chinh       -> AMENDS, confidence thấp hơn (đính chính
                                     là sửa lỗi chính tả/kỹ thuật, nhẹ hơn sửa
                                     đổi nội dung nhưng dùng chung enum AMENDS
                                     vì RelationType không có loại riêng)
  huong_dan/duoc_huong_dan       -> IMPLEMENTS (văn bản hướng dẫn thi hành)
  duoc_dan_chieu                 -> REFERENCES (dẫn chiếu trong nội dung)
  duoc_can_cu                    -> REFERENCES, confidence thấp hơn (căn cứ
                                     ban hành — quan hệ pháp lý nền tảng, khác
                                     bản chất dẫn chiếu nội dung nhưng vẫn là
                                     một dạng "tham chiếu tới")
  hop_nhat                       -> REPLACES, confidence thấp hơn (văn bản
                                     hợp nhất thay thế việc phải đọc gộp bản
                                     gốc + các bản sửa đổi)
  khac_chua_phan_loai             -> REFERENCES, confidence thấp (0.4) — raw
                                     data tự ghi chú "cần đối chiếu thủ công",
                                     giữ lại kèm metadata để review sau thay
                                     vì bỏ mất thông tin

Không map được: quan hệ mâu thuẫn (CONFLICTS_WITH) — vbpl.vn không có mục
này trong tab Lược đồ, phải xác định thủ công/riêng (xem brief mục Huy).

Bỏ qua (skip), không lỗi:
  - Cả file nếu `doc_number` của chính file đó không khớp document nào trong
    DB (văn bản được thảo luận nhưng chưa ingest, vd VBHN 28/2023) — log để
    biết, không insert.
  - Từng quan hệ riêng lẻ nếu `doc_number` bên được tham chiếu không có trong
    DB (văn bản nền/gốc như Hiến pháp, Luật cũ trước 2018 — ngoài phạm vi 14
    văn bản corpus hiện tại).
  - Quan hệ tự trỏ về chính nó (vi phạm CHECK ck_document_relations_no_self).

Idempotent: xóa mọi relation có `metadata_extra->>'import_source'` = giá trị
của script này trước khi nạp lại (không đụng tới relation được tạo thủ công/
nguồn khác).
"""

from __future__ import annotations

import asyncio
import json
import sys
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path

import structlog
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.core.logging import configure_logging
from app.models.entities import DocumentRelation
from app.models.enums import RelationType
from app.models.orm import DocumentModel, DocumentRelationModel
from app.repositories.relation_store import PgDocumentRelationRepository

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
RELATIONS_DIR = REPO_ROOT / "data" / "discovery" / "relations"
_IMPORT_TAG = "vbpl_relations_import"


@dataclass(frozen=True)
class _Mapping:
    relation_type: RelationType
    reversed_direction: bool  # True: source=văn bản tham chiếu, target=chính nó
    confidence: float


_RELATION_MAP: dict[str, _Mapping] = {
    "thay_the": _Mapping(RelationType.REPLACES, False, 1.0),
    "bi_thay_the": _Mapping(RelationType.REPLACES, True, 1.0),
    "sua_doi_bo_sung": _Mapping(RelationType.AMENDS, False, 1.0),
    "dinh_chinh": _Mapping(RelationType.AMENDS, False, 0.9),
    "bi_dinh_chinh": _Mapping(RelationType.AMENDS, True, 0.9),
    "huong_dan": _Mapping(RelationType.IMPLEMENTS, False, 1.0),
    "duoc_huong_dan": _Mapping(RelationType.IMPLEMENTS, True, 1.0),
    "duoc_dan_chieu": _Mapping(RelationType.REFERENCES, False, 1.0),
    "duoc_can_cu": _Mapping(RelationType.REFERENCES, False, 0.8),
    "hop_nhat": _Mapping(RelationType.REPLACES, False, 0.7),
    "khac_chua_phan_loai": _Mapping(RelationType.REFERENCES, False, 0.4),
}


def _norm(value: str) -> str:
    """NFC-normalize — tránh lệch Unicode giữa dữ liệu crawl và DB (đã từng
    gặp bug tương tự khi parse lãi suất Vietinbank, xem ingest_bank_rates.py)."""
    return unicodedata.normalize("NFC", value).strip()


@dataclass
class _Stats:
    files_total: int = 0
    files_resolved: int = 0
    files_skipped: list[str] | None = None
    unknown_keys: set[str] | None = None
    refs_unresolved: int = 0
    self_relations_skipped: int = 0
    relations_by_type: dict[str, int] | None = None

    def __post_init__(self) -> None:
        self.files_skipped = []
        self.unknown_keys = set()
        self.relations_by_type = {}


async def _load_doc_number_map(session) -> dict[str, uuid.UUID]:
    result = await session.execute(
        select(DocumentModel.doc_number, DocumentModel.id).where(
            DocumentModel.doc_number.is_not(None),
            DocumentModel.deleted_at.is_(None),
        )
    )
    return {_norm(doc_number): doc_id for doc_number, doc_id in result.all()}


def _build_relations_for_file(
    file_path: Path,
    doc_map: dict[str, uuid.UUID],
    stats: _Stats,
) -> list[DocumentRelation]:
    data = json.loads(file_path.read_text(encoding="utf-8"))
    this_doc_number = _norm(str(data.get("doc_number", "")))
    this_id = doc_map.get(this_doc_number)
    if this_id is None:
        stats.files_skipped.append(f"{file_path.name} (doc_number={this_doc_number!r})")
        return []
    stats.files_resolved += 1

    relations: list[DocumentRelation] = []
    seen: set[tuple[uuid.UUID, uuid.UUID, RelationType]] = set()

    for raw_key, block in data.get("relations", {}).items():
        mapping = _RELATION_MAP.get(raw_key)
        if mapping is None:
            stats.unknown_keys.add(raw_key)
            continue

        for ref in block.get("documents", []):
            ref_doc_number = _norm(str(ref.get("doc_number", "")))
            ref_id = doc_map.get(ref_doc_number)
            if ref_id is None:
                stats.refs_unresolved += 1
                continue

            source_id, target_id = (
                (ref_id, this_id) if mapping.reversed_direction else (this_id, ref_id)
            )
            if source_id == target_id:
                stats.self_relations_skipped += 1
                continue

            dedup_key = (source_id, target_id, mapping.relation_type)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            relations.append(
                DocumentRelation(
                    id=uuid.uuid4(),
                    source_doc_id=source_id,
                    target_doc_id=target_id,
                    relation_type=mapping.relation_type,
                    confidence=mapping.confidence,
                    description=block.get("label_vi"),
                    metadata_extra={
                        "import_source": _IMPORT_TAG,
                        "raw_relation_key": raw_key,
                        "ref_doc_number": ref.get("doc_number"),
                        "ref_title": ref.get("title"),
                        "source_url": data.get("source_url"),
                    },
                )
            )
            type_key = mapping.relation_type.value
            stats.relations_by_type[type_key] = stats.relations_by_type.get(type_key, 0) + 1

    return relations


async def main() -> None:
    if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    configure_logging(settings.LOG_LEVEL)

    files = sorted(RELATIONS_DIR.rglob("*.json"))
    if not files:
        print(f"Không tìm thấy file quan hệ nào trong {RELATIONS_DIR}.")
        return

    stats = _Stats(files_total=len(files))

    async with AsyncSessionFactory() as session:
        doc_map = await _load_doc_number_map(session)

        await session.execute(
            delete(DocumentRelationModel).where(
                DocumentRelationModel.metadata_extra["import_source"].astext
                == _IMPORT_TAG
            )
        )

        all_relations: list[DocumentRelation] = []
        for file_path in files:
            all_relations.extend(_build_relations_for_file(file_path, doc_map, stats))

        repo = PgDocumentRelationRepository(session)
        await repo.bulk_insert(all_relations)
        await session.commit()

    print(f"Files: {stats.files_resolved}/{stats.files_total} resolved được doc_number gốc.")
    if stats.files_skipped:
        print("Bỏ qua (văn bản chưa ingest):")
        for f in stats.files_skipped:
            print(f"  - {f}")
    if stats.unknown_keys:
        print(f"Raw relation key chưa biết (bỏ qua): {sorted(stats.unknown_keys)}")
    print(f"Quan hệ tự trỏ chính nó (bỏ qua): {stats.self_relations_skipped}")
    print(f"Tham chiếu không resolve được (văn bản ngoài corpus, bỏ qua): {stats.refs_unresolved}")
    print(f"\nĐã nạp {len(all_relations)} document_relations:")
    for rel_type, count in sorted(stats.relations_by_type.items()):
        print(f"  {rel_type:<15} {count}")


if __name__ == "__main__":
    asyncio.run(main())
