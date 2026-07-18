# Plan: Nạp corpus `data/raw/` + lớp lọc Ontology (adapt vào kiến trúc hiện tại)

## Context

Sau khi merge `main`, repo có thêm: corpus 14 văn bản pháp lý (`data/raw/`), tài liệu
`doc/Ontology_Implementation_Proposal.md`, và một số file từ nhánh main. Vấn đề:

- **DB đang rỗng** (vừa truncate) và **corpus chưa được nạp** → chat không có dữ liệu thật.
- Ontology proposal + các file merge (`backend/migrations/0001_init.sql` với RPC
  `match_document_chunks`, `backend/scripts/ingest.py`, `backend/app/services/llm_service.py`)
  được viết cho **schema Supabase cũ** (`document_chunks` clause-per-row + RPC). **Schema đó
  KHÔNG live.** Kiến trúc thật đang chạy là **Alembic + async SQLAlchemy**: `documents` →
  `chunks` (UUID, one-to-many), hybrid BM25+vector, KI pipeline đã refactor.
- `scripts/ingest.py` **hỏng** (gọi `get_settings()`, `get_vector_store()`, `add_clauses()`
  đều không tồn tại). `llm_service.py` **trùng lặp** `deepseek_service.py`. `document_loader.py`
  **mồ côi nhưng hữu ích** — parse đúng format `data/raw/*.md` thành `Clause`.
- **3 bug** proposal nêu trong `document_relation_service.py` đã **được sửa/tránh** bởi bản
  refactor hiện tại (xác minh: dedup theo `document_id` không theo title; expansion lấy
  relations không kéo chunk; conflict dùng `section_title` + explicit relations).

**Mục tiêu (đã chốt với user):** nạp corpus qua **script chuyên dụng** vào schema Alembic
live, và ánh xạ ý tưởng ontology (doc_class, trạng thái hiệu lực, đối tượng áp dụng, category,
bank attribution) vào **`metadata_extra` JSONB** + `MetadataFilter` sẵn có — **KHÔNG** tạo cột
SQL mới, **KHÔNG** dùng RPC Supabase. Lớp C `bank_products` **hoãn** (ngoài scope lần này).

**Nguyên tắc tách trục trạng thái:** `documents.status` (enum pipeline: UPLOADED/PROCESSING/
READY/...) khác với **trạng thái hiệu lực pháp lý** (`hieu_luc`/`het_hieu_luc`/
`mot_phan_het_hieu_luc`) trong header corpus. Doc nạp bằng script để `status=READY`; trạng thái
hiệu lực lưu ở `metadata_extra["legal_status"]`.

---

## Phase A — Dọn file merge chết (giảm nhiễu, tránh dùng nhầm schema)

| File | Hành động | Lý do |
|---|---|---|
| `backend/migrations/0001_init.sql` | **Xóa** | Schema Supabase `document_chunks` + RPC không live, gây hiểu nhầm. Migration thật là Alembic `alembic/versions/001-004`. |
| `backend/app/services/llm_service.py` | **Xóa** | Trùng `app/generation/llm/deepseek_service.py` (bản async đầy đủ, đang dùng). Không nơi nào import bản này trong luồng live. |

Trước khi xóa: `grep -rn "llm_service\|0001_init\|match_document_chunks\|document_chunks" backend/app`
để chắc không còn import sống. `document_loader.py` **giữ lại** (script sẽ dùng).

---

## Phase B — Script nạp corpus (lõi) — `backend/scripts/ingest.py` (viết lại)

Viết lại hoàn toàn file hỏng, dùng **document_loader + repos live + embedding service thật**.
Chạy: `cd backend && python -m scripts.ingest` (cần embedding-service ở `localhost:8001`, DB ở
`5434` — đều đang chạy qua docker).

Luồng:

1. **Load** `data/raw/` bằng `document_loader.load_documents("../data/raw")` → `list[Clause]`
   (mỗi Clause = 1 Điều: `doc_id`, `title`, `effective_date`, `status`, `clause` heading, `content`).
2. **Gom theo `doc_id`** (14 nhóm). Với mỗi văn bản:
   - Tạo `Document` entity (`app/models/entities.py:22`) với các field bắt buộc, tổng hợp cho
     nguồn markdown (không có file upload thật):
     - `title` = Clause.title; `doc_number` = doc_id
     - `doc_type`/`authority_level` = enum thô suy từ doc_id (xem Phase C, để thỏa CHECK
       constraint của migration 001/004)
     - `effective_date` = parse `Clause.effective_date` (YYYY-MM-DD)
     - `status = DocumentStatus.READY`, `version=1`
     - `filename` = tên file .md, `original_filename` = như filename,
       `content_type="text/markdown"`, `file_size = len(bytes)`,
       `file_path` = đường dẫn tương đối, `content_hash = sha256(file bytes)` (cột UNIQUE)
     - `metadata_extra` = dict ontology (Phase C)
   - `PgDocumentRepository.create(document)` (`document_store.py:93`).
   - Tạo `list[Chunk]`: mỗi Clause → 1 `Chunk` (`entities.py:86`), `chunk_index` tuần tự,
     `chunk_type=ChunkType.ARTICLE`, `section_title = Clause.clause` (heading "Điều N. ..."),
     `content = Clause.content`, `metadata_extra` = cùng dict ontology (để `merged` trong
     retriever có sẵn doc_class/category/legal_status).
   - `PgChunkRepository.bulk_insert(chunks)` (`document_store.py:221`).
3. **Embed**: sau khi insert xong mỗi doc, gọi `EmbeddingService.embed_document(doc.id)`
   (`embedding_service.py:45`) — nó tự batch, gọi embedding-service, `bulk_update_embeddings`.
   Chạy tuần tự 14 doc cho đơn giản/ổn định.
4. In report: doc_id | số Điều | legal_status | doc_class.

**Idempotency:** đầu script, nếu `PgDocumentRepository.get_by_checksum(hash)` trả doc cũ →
skip hoặc soft-delete+re-insert (đề xuất: xóa sạch rồi nạp lại để đơn giản trong hackathon;
DB vừa truncate nên lần đầu không đụng).

---

## Phase C — Enrich metadata ontology (vào `metadata_extra`, KHÔNG đổi schema)

Helper trong script (hoặc `document_loader.py`), suy từ `doc_id` — không sửa 14 file .md:

```python
def infer_doc_class(doc_id: str) -> str:      # ontology class (tiếng Việt, dùng để lọc)
    if "VBHN" in doc_id: return "thong_tu_hop_nhat"
    if "TT-"  in doc_id: return "thong_tu"
    if "NĐ-CP" in doc_id or "ND-CP" in doc_id: return "nghi_dinh"
    if "QĐ-"  in doc_id or "QD-" in doc_id: return "quyet_dinh"
    if "PL-"  in doc_id: return "phap_lenh"
    if "QH"   in doc_id: return "luat"
    return "cong_van"
```

Map enum thô cho cột DB (thỏa CHECK constraint) — tách khỏi doc_class tinh:

| doc_class | `documents.doc_type` | `documents.authority_level` |
|---|---|---|
| luat, phap_lenh | LAW | NATIONAL_LAW |
| nghi_dinh | DECREE | UNKNOWN |
| quyet_dinh | DECISION | NHNN_DECISION |
| thong_tu, thong_tu_hop_nhat | CIRCULAR | NHNN_CIRCULAR |

`metadata_extra` mỗi doc/chunk chứa:
- `doc_class`: kết quả `infer_doc_class`
- `legal_status`: `Clause.status` (`hieu_luc`/`het_hieu_luc`/`mot_phan_het_hieu_luc`)
- `category`: tên thư mục cha (`lai_suat`/`bao_hiem`/`ngoai_hoi`/`rut_truoc_han`/
  `to_chuc_tin_dung`) — **MetadataFilter đã đọc `category` sẵn** (`vector_store.py:186`)
- `doi_tuong_ap_dung`: list, bảng hằng số theo doc_id (đã biết từ nội dung thật):
  - `48/2018/TT-NHNN` → `["ca_nhan"]` (Điều 3 chỉ cá nhân)
  - `49/2018`, `48/2024`, `04/2022`, nhóm `to_chuc_tin_dung`, `ngoai_hoi` → `["ca_nhan","doanh_nghiep"]`
  - nhóm `bao_hiem` → `["ca_nhan"]`

Lưu **ở cả document-level `metadata_extra`** (vì `MetadataFilter` join `DocumentModel`) **và
chunk-level** (để `merged` trong `SearchResult` có đủ). `bank = None` cho toàn corpus pháp lý.

---

## Phase D — Retrieval lọc theo ontology + attribution

### D1. Lọc `het_hieu_luc` khi retrieval (quan trọng: corpus có 06/2012/QH13 het_hieu_luc)
`MetadataFilter.build()` (`vector_store.py:140`) hiện chỉ lọc `deleted_at IS NULL`. Thêm 3
field vào `SearchFilters` (`vector_store.py:110`) và điều kiện tương ứng trong `build()`:
- `exclude_expired: bool = True` → mặc định thêm
  `DocumentModel.metadata_extra["legal_status"].astext != "het_hieu_luc"`
- `doc_class: str | None` → `metadata_extra["doc_class"].astext == doc_class`
- `doi_tuong: str | None` → containment trên `metadata_extra["doi_tuong_ap_dung"]`
  (JSONB `@>`), bỏ qua nếu None

Điều kiện cộng ở cả `VectorRetriever` (dòng 244) và `BM25Retriever` (chúng đều gọi
`self._filter.build(filters)`), nên chỉ cần sửa `MetadataFilter` + `SearchFilters`.

### D2. Intent routing tối thiểu — `rag_service.py:retrieve` (dòng 58)
Trước khi build retriever, nếu caller không truyền filters: keyword/regex đơn giản trên query
để set `SearchFilters` (đủ cho 48h, không cần LLM):
- Query chứa "doanh nghiệp"/"công ty"/"tổ chức" → `doi_tuong="doanh_nghiep"`
- Query chứa tên ngân hàng (SHB/BIDV/Vietcombank/...) → `bank=<tên>` (đã có field, hiện chưa có
  data bank nhưng để sẵn cho Lớp C sau)
- Luôn `exclude_expired=True`

### D3. Source attribution — `models/schemas.py` + `chat_service.py`
- `Source` (`schemas.py:533`) đã có `bank`; thêm `doc_class: str | None = None`.
- Chỗ build `Source` trong `chat_service.py` (khu vực format response): set
  `doc_class` từ `SearchResult.metadata.get("doc_class")`. Giúp câu trả lời phân biệt
  "theo Thông tư NHNN" vs (sau này) "theo SHB".

---

## Phase E — Guard conflict false-positive (kiểm tra + rào, không rewrite)

`document_relation_service.py:detect_conflicts` (~dòng 596) flag conflict khi
`a.section_title == b.section_title` giữa 2 doc khác nhau. Corpus có **rất nhiều** Điều trùng
tiêu đề ("Điều 1. Phạm vi điều chỉnh", "Điều 2. Đối tượng áp dụng") → nguy cơ conflict giả.
- **Xác minh trước**: `detect_conflicts()` có được wire vào luồng chat không, hay pipeline chỉ
  dùng `ConflictDetectionProcessor` (explicit `CONFLICTS_WITH` relations, ~dòng 337)? Đọc
  `chat_service.py` + `KnowledgePipeline` để chốt.
- **Nếu có wire**: thêm điều kiện chỉ coi là conflict khi 2 doc **cùng `category`** *hoặc* có
  quan hệ trong `document_relations`. Nếu không wire → chỉ ghi chú, không sửa.

---

## Files touched

**Xóa:** `backend/migrations/0001_init.sql`, `backend/app/services/llm_service.py`
**Viết lại:** `backend/scripts/ingest.py`
**Sửa:** `backend/app/repositories/vector_store.py` (`SearchFilters` + `MetadataFilter.build`),
`backend/app/services/rag_service.py` (intent routing), `backend/app/models/schemas.py`
(`Source.doc_class`), `backend/app/services/chat_service.py` (set doc_class vào Source),
có thể `backend/app/repositories/document_loader.py` (thêm helper infer/mapping) hoặc để helper
trong script.
**Không đổi:** ORM/migrations (không cột mới), `deepseek_service.py`, chunkers/parsers.

## Reuse (không viết mới)
- `document_loader.load_documents` / `_parse_document` — parser corpus (`document_loader.py:35`)
- `PgDocumentRepository.create` / `get_by_checksum`, `PgChunkRepository.bulk_insert`
  (`document_store.py:93,170,221`)
- `EmbeddingService.embed_document` (`embedding_service.py:45`)
- `MetadataFilter` đọc `metadata_extra` cho `bank`/`category` (`vector_store.py:181-189`) — mở
  rộng cùng pattern
- Entities `Document`/`Chunk` (`entities.py:22,86`), enum `ChunkType.ARTICLE`,
  `DocumentStatus.READY`

---

## Verification (Definition of Done)

1. `cd backend && python -m scripts.ingest` → report 14 doc, tổng ~474 Điều; không lỗi.
2. SQL spot-check: `SELECT metadata_extra->>'doc_class', metadata_extra->>'legal_status',
   metadata_extra->>'category' FROM chunks LIMIT ...` — mọi row có đủ 3 field; nhóm `bao_hiem`
   có `doi_tuong_ap_dung=["ca_nhan"]`.
3. `SELECT count(*) FROM chunks WHERE embedding IS NOT NULL` = tổng số chunk (embed xong).
4. `POST /api/v1/chat {"message":"hạn mức bảo hiểm tiền gửi là bao nhiêu"}` (qua docker,
   UTF-8): trả 200; `sources` chứa Luật 111/2025 + QĐ 32/2021/TT 04/2026, **KHÔNG** chứa Luật
   06/2012 (`het_hieu_luc` bị lọc — D1); không mất Điều cùng văn bản.
5. `POST /api/v1/chat {"message":"lãi suất tiền gửi doanh nghiệp"}`: intent routing set
   `doi_tuong=doanh_nghiep`; sources không gồm 48/2018 (chỉ cá nhân).
6. Response bất kỳ: không có conflict giả giữa 2 văn bản chỉ trùng tiêu đề Điều (Phase E).
7. `grep -rn "llm_service\|match_document_chunks" backend/app` → rỗng (dead code đã xóa).

## Out of scope (hoãn sau hackathon)
Lớp C `bank_products` + so sánh SQL; tách Khoản/Điểm; parser PDF ngân hàng; markdown parser
tích hợp vào pipeline 5-stage (đã chọn script thay thế).
