# Đề xuất implement Ontology Model vào kiến trúc hiện tại

Đối tượng đọc: **architecture engineer** (Phúc). Tài liệu này validate bản thiết kế
`data/discovery/ontology-tien-gui.md` với **code thật trên nhánh này** và **corpus thật đã
convert** (`data/raw/` — 14 văn bản, 474 Điều, PR #8), rồi đưa các bước implement cụ thể.

Files đã đối chiếu trực tiếp: `document_loader.py`, `vector_store.py`, `relation_store.py`,
`rag_service.py`, `document_relation_service.py`, `chat_service.py`, `guardrail_service.py`,
`models/schemas.py`, `core/config.py`, `migrations/0001_init.sql`, `scripts/ingest.py`.

---

## 1. Verdict tổng quan

| Phần trong ontology-tien-gui.md | Verdict | Ghi chú |
|---|---|---|
| Mô hình 3 lớp (A pháp lý / B nghiệp vụ / C thị trường) | ✅ Giữ nguyên | Khớp bản chất dữ liệu thật |
| Mapping Điều → class (mục 3) | ✅ Giữ nguyên | Đã grounded trên văn bản thật |
| Migration 0002 (mục 4) | ⚠️ **Có 2 lỗi SQL chạy là hỏng** — dùng bản đã sửa ở mục 4 dưới đây | FK không hợp lệ; CHECK vô hiệu |
| Enum `doc_class` | ⚠️ Thiếu 2 giá trị so với dữ liệu thật trên main | Thiếu `thong_tu_hop_nhat` (VBHN 28/2023 đã merge), `van_ban_noi_bo` |
| 2 relation type mới (`huong_dan_boi`, `quy_dinh_chi_tiet`) | ⚠️ Là quan hệ gần trùng/nghịch đảo — đề xuất **sửa lại quyết định 6.1**: gộp 1 loại + quy ước chiều | Xem 2.3 |
| Regex Khoản/Điểm (mục 5, quyết định 6.2) | ⚠️ Đề xuất **hoãn sang sau hackathon** | Điều-level đã chạy end-to-end (474 chunk validate xong); tách Khoản tăng 3x số chunk + rủi ro tách sai, không chặn demo |
| Bảng `bank_products` (mục 4.3) | ⚠️ Đúng hướng nhưng thiếu upsert key + trộn dữ liệu bảng với tài liệu dài | Xem 2.4 |
| Retrieval filter theo metadata | ❌ **Ontology doc thêm cột + index nhưng không sửa RPC** — cột sẽ nằm chết | Xem 2.2, bắt buộc sửa `match_document_chunks` |

**Kết luận**: khả thi, nhưng KHÔNG copy nguyên văn SQL mục 4 của ontology doc. Ngoài ra
validate với corpus thật phát hiện **3 bug có sẵn trong pipeline hiện tại sẽ phát nổ ngay khi
ingest 474 chunk** (mục 3) — phải sửa trước hoặc cùng lúc với ontology, nếu không demo sai
trước khi ontology kịp có tác dụng.

---

## 2. Chi tiết các điểm cần sửa so với ontology doc

### 2.1 Hai lỗi SQL trong migration 0002 gốc

1. `quy_dinh_boi text references document_chunks(doc_id)` — **fail ngay khi chạy migration**:
   `doc_id` không unique (mỗi Điều 1 row, 474 rows / 14 doc_id). Postgres đòi cột được
   reference phải có UNIQUE constraint. Sửa: bỏ FK, lưu cặp `(quy_dinh_boi_doc_id,
   quy_dinh_boi_clause)` dạng text thường, validate ở app layer. Điều này còn đúng ontology
   hơn: `quyDinhBoi` phải trỏ tới **Điều cụ thể**, không phải cả văn bản.

2. `check (channel in ('tai_quay','online', null))` — **constraint vô hiệu hoàn toàn**:
   `'xyz' IN (..., NULL)` cho kết quả `NULL` (unknown), CHECK chỉ reject khi `FALSE` → mọi giá
   trị đều lọt. Sửa: bỏ `null` khỏi list (NULL tự pass CHECK đúng chuẩn SQL).

### 2.2 RPC `match_document_chunks` phải đổi signature — đây là chỗ ontology "sống" hay "chết"

Nguyên tắc cốt lõi của plan gốc: *"lọc cứng theo metadata TRƯỚC similarity search"*. Hiện tại
RPC (0001_init.sql) chỉ lọc `status <> 'het_hieu_luc'`. Ontology doc thêm cột `doc_class` +
index nhưng không đề xuất chỗ nào tiêu thụ nó → thêm cột vô nghĩa. Bản sửa ở mục 4 thêm 3
tham số filter nullable (`filter_doc_class`, `filter_bank`, `filter_doi_tuong`) — backward
compatible (caller cũ không truyền gì vẫn chạy).

### 2.3 Sửa lại quyết định 6.1: gộp `huong_dan_boi` + `quy_dinh_chi_tiet` thành 1 loại

Trong thực tiễn pháp lý VN, "quy định chi tiết" và "hướng dẫn thi hành" đi chung một cụm —
chính vbpl.vn (nguồn crawl) gộp làm 1 loại (`huong_dan`, referenceType=9 trong schema B).
Tách 2 enum value mà không định nghĩa chiều sẽ tạo dữ liệu nhập nhằng (row `(A, B,
huong_dan_boi)` nghĩa là A hướng dẫn B hay ngược lại?). Đề xuất:

- 1 relation_type duy nhất: **`huong_dan`**, quy ước chiều cố định:
  `source_doc_id` = văn bản hướng dẫn/quy định chi tiết, `related_doc_id` = văn bản được
  hướng dẫn. Ví dụ: `(04/2026/TT-NHNN, 111/2025/QH15, huong_dan)`.
- Cần chiều ngược ("văn bản này được hướng dẫn bởi ai") → query đảo cột, không cần loại mới.

*Đây là revision so với quyết định đã chốt 6.1 — cần Huy/team xác nhận lại. Nếu team vẫn
muốn giữ 2 tên riêng thì bắt buộc kèm bảng quy ước chiều cho từng loại vào README migration.*

### 2.4 `bank_products`: giới hạn cho dữ liệu dạng bảng + thêm upsert key

- **Upsert key**: không có unique constraint thì chạy ingest 2 lần → câu "ngân hàng nào lãi
  suất cao nhất" trả kết quả trùng. Thêm `unique (bank, product_name, term, customer_segment,
  channel_key, effective_date)` (dùng generated column `channel_key` vì `channel` nullable —
  NULL không tham gia unique constraint chuẩn SQL).
- **Chỉ chứa dữ liệu bảng** (`lai_suat_tien_gui`, `bieu_phi` dạng số). T&C/thủ tục mở sổ là
  tài liệu dài — nếu nhét vào 1 row `content` sẽ thành blob khổng lồ không chunk được. Đề
  xuất: T&C/thủ tục ingest vào `document_chunks` như văn bản thường với `doc_class =
  'van_ban_noi_bo'` + cột mới `bank` — được luôn 2 việc: chunk theo cấu trúc sẵn có, và
  `Source` trong API trả lời được "theo quy định SHB".

---

## 3. Ba bug pipeline hiện tại sẽ phát nổ khi ingest corpus thật (phát hiện khi validate)

Đây là phát hiện mới, chưa có trong ontology doc — nhưng liên quan trực tiếp: **ontology
metadata chính là cách sửa đúng các bug này.**

### Bug 1 — `apply_amendment` khử trùng theo `title` → mất Điều cùng văn bản
`document_relation_service.py:17-25`: dict key theo `c.title`, chỉ giữ 1 chunk mới nhất.
Nhưng **các Điều cùng 1 văn bản có cùng title và cùng effective_date** → top-5 retrieval trả
3 Điều của Luật 111/2025 thì sau bước này chỉ còn 1 Điều (giữ chunk gặp đầu tiên). Với corpus
474 Điều, gần như mọi câu trả lời sẽ bị mất context đúng.
**Sửa**: chỉ khử trùng giữa các văn bản có quan hệ `amends`/`supersedes` trong
`document_relations` (đúng thiết kế ontology `thayThe`), không bao giờ khử 2 chunk cùng
`doc_id`. Key so sánh: cặp doc_id có quan hệ, giữ doc có `effective_date` mới hơn.

### Bug 2 — `apply_cross_reference` kéo TOÀN BỘ văn bản liên quan vào context
`document_relation_service.py:40-53` gọi `query_by_doc_id` (lấy **hết** chunk của văn bản
liên quan). Chunk từ Luật 96/2025 có cross-reference tới Luật 32/2024 → **kéo cả 210 Điều**
vào context → tràn context window của LLM, tăng cost, loãng câu trả lời.
**Sửa**: giới hạn mở rộng — chỉ lấy top-N (đề xuất N=3) chunk của văn bản liên quan có
similarity cao nhất với query gốc (thêm param `limit` + rank bằng embedding có sẵn), hoặc
tối thiểu là `.limit(3)` trên query Supabase.

### Bug 3 — `detect_conflicts` báo mâu thuẫn giả giữa các văn bản không liên quan
`document_relation_service.py:76-77`: `_same_topic` coi 2 chunk "cùng chủ đề" nếu **cùng số
Điều** (`clause.split(".")[0]`). "Điều 1" của TT 48/2018 (tiền gửi tiết kiệm) vs "Điều 1"
của NĐ 68/2013 (bảo hiểm tiền gửi) → khác nội dung → báo conflict. Với 14 văn bản đều có
Điều 1-5, mọi response sẽ ngập cảnh báo mâu thuẫn giả.
**Sửa**: điều kiện same-topic phải dựa trên quan hệ thật: 2 doc có quan hệ
`amends`/`supersedes`/`huong_dan` trong `document_relations`, HOẶC cùng `doc_class` + cùng
nhóm thư mục nguồn. Số Điều trùng nhau không mang nghĩa gì giữa 2 văn bản khác nhau.

---

## 4. Migration `0002_ontology.sql` — bản đã sửa, chạy được

```sql
-- ============================================================
-- 1. Quan hệ văn bản: thêm 'huong_dan' (gộp huongDanBoi/quyDinhChiTiet — mục 2.3)
--    Quy ước chiều: source_doc_id LÀ văn bản hướng dẫn, related_doc_id LÀ văn bản được hướng dẫn
-- ============================================================
alter table document_relations drop constraint if exists document_relations_relation_type_check;
alter table document_relations add constraint document_relations_relation_type_check
    check (relation_type in ('cross_reference', 'amends', 'supersedes', 'huong_dan'));

-- ============================================================
-- 2. Metadata ontology cho Lớp A/B trên document_chunks
--    (khoan/diem để sẵn nullable — Điều-level trước, Khoản/Điểm hoãn sau hackathon)
-- ============================================================
alter table document_chunks add column if not exists doc_class text
    check (doc_class in ('luat','nghi_dinh','thong_tu','thong_tu_hop_nhat',
                         'phap_lenh','quyet_dinh','cong_van','van_ban_noi_bo'));
alter table document_chunks add column if not exists bank text;          -- null = văn bản pháp lý
alter table document_chunks add column if not exists doi_tuong_ap_dung text[];
alter table document_chunks add column if not exists khoan text;
alter table document_chunks add column if not exists diem text;

create index if not exists document_chunks_doc_class_idx on document_chunks (doc_class);
create index if not exists document_chunks_bank_idx on document_chunks (bank);

-- ============================================================
-- 3. RPC v2 — lọc cứng metadata TRƯỚC vector search (mục 2.2)
--    Backward compatible: caller cũ không truyền filter vẫn chạy như cũ
-- ============================================================
create or replace function match_document_chunks(
    query_embedding vector(1024),
    match_count int default 5,
    filter_doc_class text default null,
    filter_bank text default null,
    filter_doi_tuong text default null
)
returns table (
    doc_id text, title text, clause text, effective_date date,
    status text, content text, similarity float
)
language sql stable
as $$
    select doc_id, title, clause, effective_date, status, content,
           1 - (embedding <=> query_embedding) as similarity
    from document_chunks
    where status <> 'het_hieu_luc'
      and (filter_doc_class is null or doc_class = filter_doc_class)
      and (filter_bank is null or bank = filter_bank)
      and (filter_doi_tuong is null or doi_tuong_ap_dung @> array[filter_doi_tuong])
    order by embedding <=> query_embedding
    limit match_count;
$$;

-- ============================================================
-- 4. Lớp C — bảng số liệu ngân hàng (CHỈ lãi suất/phí dạng bảng; T&C đi vào
--    document_chunks với doc_class='van_ban_noi_bo' + bank — mục 2.4)
-- ============================================================
create table if not exists bank_products (
    id                bigint generated always as identity primary key,
    bank              text not null,
    product_category  text not null check (product_category in ('lai_suat_tien_gui','bieu_phi')),
    product_name      text not null,
    term              text,
    customer_segment  text not null default 'ca_nhan'
        check (customer_segment in ('ca_nhan','doanh_nghiep')),
    channel           text check (channel in ('tai_quay','online')),  -- NULL tự pass, KHÔNG đưa null vào IN
    rate_value        numeric(6,3),
    content           text not null,
    embedding         vector(1024),
    source_url        text,
    effective_date    date not null,
    quy_dinh_boi_doc_id  text,   -- trỏ Điều cụ thể Lớp A, validate ở app layer (không FK được vì doc_id không unique)
    quy_dinh_boi_clause  text,
    channel_key       text generated always as (coalesce(channel, 'all')) stored,
    created_at        timestamptz not null default now(),
    unique (bank, product_name, term, customer_segment, channel_key, effective_date)  -- chống trùng khi re-ingest
);

create index if not exists bank_products_lookup_idx on bank_products (bank, product_category, term);
create index if not exists bank_products_embedding_idx on bank_products using hnsw (embedding vector_cosine_ops);
```

---

## 5. Các bước implement cụ thể (theo thứ tự, có file đích)

### Phase 0 — Sửa 3 bug pipeline (BLOCKING, làm trước ingest) — ~2-3h
| File | Thay đổi |
|---|---|
| `document_relation_service.py:17-25` | `apply_amendment`: chỉ dedup giữa doc có quan hệ `amends`/`supersedes`; không bao giờ loại chunk cùng `doc_id` |
| `document_relation_service.py:40-53` + `vector_store.py:70` | `query_by_doc_id(doc_id, limit=3)` hoặc rank theo similarity với query; chặn kéo nguyên 210 Điều |
| `document_relation_service.py:76-77` | `_same_topic`: bỏ so sánh số Điều; điều kiện = 2 doc có quan hệ trong `document_relations` |
| Test | Unit test với corpus giả 2 văn bản × 3 Điều; ingest thật `data/raw/` rồi hỏi 5 câu FAQ mẫu, kiểm sources không mất Điều cùng văn bản |

### Phase 1 — Migration 0002 (mục 4 ở trên) — ~0.5h
Chạy trong Supabase SQL editor. Không phá dữ liệu cũ (toàn `add column if not exists`).

### Phase 2 — Ingest metadata ontology, KHÔNG cần đổi format data/raw — ~1.5h
`doc_class` suy ra được từ chính `doc_id` (không phải sửa 14 file md):
```python
# document_loader.py hoặc scripts/ingest.py
def infer_doc_class(doc_id: str) -> str:
    if "VBHN" in doc_id: return "thong_tu_hop_nhat"
    if "TT-" in doc_id:  return "thong_tu"
    if "NĐ-CP" in doc_id: return "nghi_dinh"
    if "QĐ-" in doc_id:  return "quyet_dinh"
    if "PL-" in doc_id:  return "phap_lenh"
    if "QH" in doc_id:   return "luat"
    return "cong_van"
```
`doi_tuong_ap_dung`: bảng hằng số mapping theo doc_id (đã biết từ nội dung thật):
TT 48/2018 → `{ca_nhan}` (Điều 3 chỉ cá nhân); TT 49/2018, 48/2024, 04/2022 →
`{ca_nhan, doanh_nghiep}`; nhóm bảo hiểm → `{ca_nhan}` (Luật BHTG chỉ bảo hiểm tiền gửi cá
nhân); Luật TCTD/ngoại hối → `{ca_nhan, doanh_nghiep}`.
`vector_store.add_clauses`: thêm 2 field vào rows insert.

### Phase 3 — Retrieval dùng filter + Source có attribution — ~2-3h
| File | Thay đổi |
|---|---|
| `vector_store.py:query` | Thêm params `doc_class/bank/doi_tuong` truyền xuống RPC |
| `rag_service.py:retrieve` | Intent routing tối thiểu: query chứa tên ngân hàng → `filter_bank`; chứa "doanh nghiệp/công ty" → `filter_doi_tuong='doanh_nghiep'` (regex/keyword là đủ cho 48h, không cần LLM classify) |
| `models/schemas.py` | `RetrievedChunk` + `Source` thêm `bank: str \| None`, `doc_class: str \| None` — client thấy rõ "theo SHB" vs "theo Thông tư NHNN" |
| `chat_service.py:54-63` | Truyền field mới vào `Source` |

### Phase 4 — Lớp C `bank_products` + đường truy vấn so sánh — ~4-6h (CÂN NHẮC HOÃN)
1. Nạp 4 nguồn JSON sạch có sẵn: BIDV/VietinBank/Vietcombank (`bank_docs/*/pages/*.json`).
2. SHB (ngân hàng chính, bảng trong PDF nhiều tầng): **nhập tay 1 lần** bảng lãi suất KHCN
   thành JSON (~1-2h người, nhanh và chính xác hơn viết parser PDF trong hackathon).
3. Route câu hỏi so sánh ("ngân hàng nào cao nhất...", "so sánh...") → SQL
   `select bank, product_name, rate_value from bank_products where term=... order by rate_value desc`
   → đưa kết quả bảng vào context, KHÔNG để LLM tự so sánh số từ chunk văn bản.
4. Techcombank hoãn (PDF phức tạp nhất, không phải ngân hàng chính).

### Phase 5 — System prompt: bản đồ khái niệm rút gọn — ~0.5h
Chỉ nhúng: tên 3 lớp + quy tắc diễn giải metadata trả về ("nếu source có `bank` → đây là số
liệu công bố của ngân hàng, kèm effective_date khi trả lời; nếu `doc_class` pháp lý → trích
số hiệu văn bản + Điều"). KHÔNG nhồi toàn bộ ontology dạng văn xuôi (đúng plan gốc).

---

## 6. Khuyến nghị phạm vi cho quỹ 48h

| Bắt buộc (demo sai nếu thiếu) | Nên có | Hoãn sau hackathon |
|---|---|---|
| Phase 0 (3 bug) | Phase 3 intent routing | Regex Khoản/Điểm (revision quyết định 6.2) |
| Phase 1 + 2 | Phase 4 bước 1-3 (SHB + 3 bank JSON) | Techcombank PDF parser |
| Phase 5 | | `bieu_phi` dạng số vào bank_products |

## 7. Definition of done
1. `python -m scripts.ingest` nạp 474 chunk, spot-check SQL: mọi row có `doc_class` đúng,
   nhóm `bao_hiem` có `doi_tuong_ap_dung={ca_nhan}`.
2. Hỏi "hạn mức bảo hiểm tiền gửi": sources chỉ chứa Luật 111/2025 + QĐ 32/2021/TT 04/2026,
   KHÔNG chứa Luật 06/2012 (het_hieu_luc), không mất Điều nào cùng văn bản (Bug 1 fixed).
3. Hỏi câu dính Luật 96/2025: context không phình 210 Điều của Luật 32/2024 (Bug 2 fixed).
4. Response bất kỳ: không có conflict giả giữa 2 văn bản chỉ trùng số Điều (Bug 3 fixed).
5. (Nếu làm Phase 4) "Ngân hàng nào lãi suất 12 tháng cao nhất?": câu trả lời lấy số từ SQL,
   sources ghi rõ bank + effective_date từng số.
