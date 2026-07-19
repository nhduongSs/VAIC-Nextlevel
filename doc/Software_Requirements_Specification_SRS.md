# Software Requirements Specification (SRS) — SỔ VÀNG
## Trợ lý AI tư vấn & so sánh tiền gửi ngân hàng

| | |
|---|---|
| **Phiên bản** | 1.0 — 2026-07-19 |
| **Chuẩn tham chiếu** | IEEE 830 / ISO-IEC-IEEE 29148 (cấu trúc rút gọn) |
| **Tài liệu liên quan** | `v2_so-vang-tai-lieu-BA.docx` (BA — nguồn FR-01…08), `doc/User_Requirements_Document_URD.md` (URD), `.ai/architecture/00–14`, `doc/Kha_nang_mo_rong_Extensibility.md` |
| **Phạm vi mã yêu cầu** | FR-01…08 kế thừa nguyên trạng từ tài liệu BA; FR-09 trở đi là yêu cầu hệ thống bổ sung do SRS định nghĩa |

---

## 1. Giới thiệu

### 1.1 Mục đích
Đặc tả yêu cầu phần mềm cho hệ thống SỔ VÀNG ở mức đủ để: (a) đội phát triển hiện thực và
kiểm thử, (b) đội nghiệp vụ/đối tác nghiệm thu, (c) truy vết hai chiều URD ↔ SRS ↔ test.

### 1.2 Phạm vi sản phẩm
Nền tảng RAG tiếng Việt cho miền tiền gửi: hỏi đáp pháp lý có trích dẫn, so sánh lãi suất
đa ngân hàng, trợ lý nội bộ cho GDV (B2B), với tầng Knowledge Intelligence (version
resolution, conflict detection, authority ranking, timeline) và guardrails. Không thực hiện
giao dịch thật ở G1–G3; không khuyến nghị đầu tư cá nhân hóa (mọi giai đoạn).

### 1.3 Định nghĩa & từ viết tắt
RAG (Retrieval-Augmented Generation) · KI (Knowledge Intelligence) · Lớp A/B/C (pháp lý /
nghiệp vụ nội bộ / thị trường) · Rate DB (`bank_products`) · GDV (giao dịch viên) · Hub
(Central Integration Hub) · BHTG (bảo hiểm tiền gửi) · NHNN (Ngân hàng Nhà nước).

### 1.4 Tổng quan hiện trạng
Các FR đánh dấu **[Đã hiện thực]** đang chạy trong repository `VAIC-Nextlevel` (backend
FastAPI `backend/app/`, frontend Next.js `frontend/`); phần còn lại theo lộ trình G2/G3/B2B+.

---

## 2. Mô tả tổng thể

### 2.1 Bối cảnh sản phẩm
Hệ độc lập, giao tiếp ngoài qua: (1) người dùng — web chat UI; (2) nguồn dữ liệu — văn bản
pháp lý (vbpl.vn) và biểu lãi suất công khai 4 ngân hàng; (3) dịch vụ AI — DeepSeek LLM
(API), BGE-M3 embedding (self-host); (4) *(B2B+)* hệ thống ngân hàng đối tác qua Central
Integration Hub (chuẩn tham chiếu: Temenos open APIs).

### 2.2 Chức năng chính
Hỏi đáp pháp lý có trích dẫn · so sánh lãi suất · KI pipeline · guardrails 3 tầng · nạp
liệu văn bản · quản trị nội dung · (B2B+) tích hợp Hub, handoff RM, tra cứu BPM, ERP-deposit.

### 2.3 Ràng buộc thiết kế
- Một PostgreSQL duy nhất (pgvector + tsvector + bảng quan hệ) — không Redis/Neo4j/Elasticsearch.
- Embedding: BAAI/bge-m3 (1024 chiều). LLM: DeepSeek (thay được qua adapter).
- Clean Architecture, Repository Pattern, Dependency Injection, async Python 3.12+/FastAPI.
- Chunking Lớp A theo ranh giới Điều; số liệu Lớp C không đưa vào embedding path khi so sánh.
- Docker Compose; CI GitHub Actions với quality gates Ruff/MyPy/Pytest.

### 2.4 Giả định & phụ thuộc
Nguồn công khai của ngân hàng duy trì định dạng truy cập được (đã có phương án 4 kỹ thuật
crawl khác nhau — xem `data/discovery/bank_docs/summary.md`); DeepSeek API khả dụng (có
retry/timeout, thông điệp degrade khi gián đoạn); quan hệ văn bản (thayThe/huong_dan/
conflict) được curate bởi con người trước khi kích hoạt.

---

## 3. Yêu cầu chức năng

> Định dạng: mỗi FR gồm mô tả, tiêu chí kiểm thử được, và trạng thái.
> FR-01…08 giữ nguyên phát biểu gốc của tài liệu BA, bổ sung đặc tả chi tiết.

### Nhóm A — Hỏi đáp & so sánh (B2C, G1–G2)

**FR-01 · Trả lời câu hỏi quyền lợi có trích dẫn điều luật** — Cao, G1 **[Đã hiện thực]**
- Endpoint `POST /api/v1/chat` (session_id, message) → answer + sources[] + conflicts[] + timeline[].
- Pipeline bắt buộc: input guard → intent routing → hybrid retrieval (BM25 + vector, metadata
  filter trước similarity) → KI pipeline → LLM (chỉ từ context) → output guard.
- Citation tối thiểu: tên văn bản, số hiệu, Điều (section_number), ngày hiệu lực, preview.
- Kiểm thử: bộ câu FAQ chuẩn (Precision@5 ≥ 85%); mọi câu trả lời pháp lý có ≥ 1 citation.

**FR-02 · Bảng so sánh lãi suất theo kỳ hạn** — Cao, G1 **[Đã hiện thực]**
- Endpoint `/rates/compare` trả về danh sách {bank, product_name, term_months, rate_value,
  effective_date} truy vấn SQL trực tiếp trên Rate DB (`bank_products`), sắp theo rate_value.
- Cấm sinh số liệu từ LLM; LLM chỉ diễn đạt kết quả SQL (nguyên tắc FR-08).
- Kiểm thử: số hiển thị khớp 100% bản ghi DB; có `effective_date` trên từng dòng.

**FR-03 · Phân biệt tiết kiệm (cá nhân) vs có kỳ hạn (cá nhân + tổ chức)** — Cao, G1 **[Đã hiện thực]**
- Metadata `doi_tuong_ap_dung` trên từng chunk; filter cứng trước vector search; intent
  routing nhận diện ngữ cảnh doanh nghiệp qua keyword.
- Kiểm thử: câu hỏi chứa "doanh nghiệp/công ty/tổ chức" không trả citation từ văn bản chỉ
  áp dụng cá nhân (TT 48/2018).

**FR-04 · Cập nhật lãi suất theo lịch, đối chiếu 2 nguồn** — Cao, G2
- Scheduler crawl định kỳ (Sơ đồ 2 tài liệu BA); chỉ ghi Rate DB khi 2 nguồn độc lập khớp
  hoặc sau khi được người vận hành xác nhận; lưu lịch sử theo `effective_date` (không ghi đè).
- Kiểm thử: bản ghi sai lệch 2 nguồn → rơi vào hàng đợi duyệt tay, không xuất hiện ở FR-02.

**FR-05 · Mở rộng nhóm ngân hàng TMCP** — Trung bình, G2
- Thêm ngân hàng = thêm connector crawl + bản ghi Rate DB; không đổi schema (NFR mở rộng).
- Kiểm thử: thêm 1 ngân hàng mới không yêu cầu migration phá vỡ và không sửa code service.

### Nhóm B — Chất lượng tri thức (KI)

**FR-07 · Cảnh báo văn bản hết hiệu lực / bản hợp nhất mới** — Trung bình, G2 **[Đã hiện thực một phần]**
- VersionResolution: quan hệ REPLACES → chunk văn bản cũ bị phạt điểm ×0.5 + version note
  "Đã bị thay thế bởi văn bản mới hơn"; filter `exclude_expired` ở tầng SQL.
- Kiểm thử: hỏi chủ đề có cặp TT 48/2018 → TT 48/2024: câu trả lời theo bản 2024, kèm note.

**FR-08 · Fact-check số liệu trước khi hiển thị** — Cao, G1 **[Đã hiện thực]**
- Mọi con số lãi suất trong câu trả lời phải đối chiếu khớp bản ghi Rate DB; sai lệch →
  chặn và thay bằng giá trị nguồn hoặc từ chối.
- Kiểm thử: fuzz câu hỏi số liệu, tỷ lệ khớp DB = 100%.

**FR-09 · Phát hiện & cảnh báo mâu thuẫn quy định** — Cao, G2 **[Đã hiện thực]**
- Quan hệ CONFLICTS_WITH curate ở mức chunk (source/target_chunk_id trong metadata); chỉ
  cảnh báo khi ≥ 1 chunk của cặp nằm trong context (logic OR); response trả `conflicts[]`
  {source_title, target_title, description, confidence}; UI hiển thị ConflictNotice 2 phía.
- Kiểm thử: `test_ki_pipeline_processors.py`; không có cảnh báo giả giữa 2 văn bản chỉ trùng
  số Điều.

**FR-10 · Timeline phiên bản văn bản** — Trung bình, G2 **[Đã hiện thực]**
- Dựng chuỗi REPLACES thành timeline {doc_number, effective_date, is_current}; expose trong
  response chat; phát hiện và log vòng lặp (circular reference).

**FR-16 · Mở rộng ngữ cảnh qua đồ thị quan hệ (cross-reference)** — Cao, G1 **[Đã hiện thực]**
- BFS trên `document_relations` (REFERENCES/IMPLEMENTS/AMENDS/SUPPLEMENTS), max 2 hops,
  cap 20 quan hệ; authority ranking (Luật 1.0 → FAQ 0.1) áp trọng số KI_AUTHORITY_WEIGHT.
- Kiểm thử: câu hỏi BHTG kéo đủ chuỗi Luật → Nghị định → Thông tư trong sources.

### Nhóm C — An toàn & tuân thủ

**FR-11 · Guardrails 3 tầng** — Cao, G1 **[Đã hiện thực]**
- Input guard: prompt injection, PII, unsafe request, whitelist chủ đề, chặn tư vấn tài
  chính cá nhân. Retrieval guard: context dưới ngưỡng liên quan → từ chối có kiểm soát.
  Output guard: lọc cụm cam kết rủi ro trước khi trả về.
- Kiểm thử: `test_guardrails.py`; bộ payload injection chuẩn bị chặn 100%; câu "nên gửi
  hay mua vàng" bị từ chối kèm giải thích.

### Nhóm D — Quản trị nội dung & vận hành

**FR-12 · Nạp liệu văn bản không cần release code** — Cao, G1 **[Đã hiện thực]**
- Quy trình: thêm file `data/raw/<loai>/*.md` (+ khai báo quan hệ nếu có) → `scripts/ingest.py`
  → parse, tách Điều, suy metadata (doc_class, doi_tuong, authority, hiệu lực), embed, upsert.
- API quản trị: documents / ingestion / embeddings / health (đã có router tương ứng).
- Kiểm thử: ingest lại toàn corpus idempotent (không nhân bản bản ghi).

**FR-13 · Observability pipeline** — Trung bình, G2 **[Đã hiện thực]**
- structlog ghi từng processor (tên, latency); mỗi response kèm statistics (số chunk, số
  citation, số conflict, expansion_count, pipeline_latency_ms).
- Kiểm thử: log truy vấn được theo session; thống kê tổng hợp được theo ngày.

### Nhóm E — Tích hợp đối tác (B2B / B2B+)

**FR-06 · Trợ lý nội bộ cho GDV** — Trung bình, G3
- Chế độ đăng nhập đối tác (JWT, phân quyền); corpus bổ sung Lớp B (quy định nội bộ đối
  tác, gắn `bank`); citation ghi rõ "theo quy định nội bộ <ngân hàng>" vs "theo Thông tư NHNN".
- Kiểm thử: người dùng đối tác A không thấy tài liệu nội bộ của đối tác B.

**FR-14 · Central Integration Hub** — Trung bình, B2B+
- Mọi truy vấn số liệu/nghiệp vụ đối tác đi qua Hub (một contract API duy nhất); connector
  theo vai trò: Fee & Rate Management (thay nguồn crawl), CRM (phân khúc — UR handoff), RM
  Workbench (handoff kèm transcript), BPM (ProcessOwnerResolver: process owner, SLA, trạng
  thái hồ sơ). Đổi hệ thống đích = cấu hình Hub, không deploy lại chatbot.
- Kiểm thử: contract test trên Hub API; thay mock CRM bằng CRM khác không sửa code chatbot.

**FR-17 · Tư vấn sản phẩm hiện có theo background khách hàng** — Cao (B2B+), sản phẩm đầu ra chủ lực của phần mở rộng
- Điều kiện kích hoạt: người dùng đã đăng nhập kênh đối tác và **opt-in** chia sẻ dữ liệu
  (ràng buộc NFR-05); không opt-in → fallback tư vấn không cá nhân hóa (FR-01/02).
- Nguồn background (qua Hub — FR-14, chatbot nhận 1 "customer background package" chuẩn hóa,
  không gọi thẳng hệ thống nguồn); đặc tả với đối tác SHB:

  | Dữ liệu | Hệ thống nguồn (SHB) |
  |---|---|
  | Danh mục sản phẩm + lãi suất niêm yết | Product Catalog / Fee & Rate Management trên core Temenos |
  | Số dư CASA, sổ đang gửi, ngày đáo hạn, lãi suất đang hưởng | Core banking Temenos (open APIs) |
  | Phân khúc (thường/ưu tiên), sản phẩm đang dùng, KYC | CRM |
  | Hành vi kênh số (kênh ưa thích, sản phẩm xem gần đây) | SHB SAHA / SHB Corporate |
  | RM phụ trách, hạn mức phê duyệt | RM Workbench + BPM |

- Xử lý: processor `ProductMatching` (thêm vào KI chain) đối chiếu background × danh mục sản
  phẩm hiện có → chọn 2–3 gợi ý; ràng buộc pháp lý và guardrails tái dùng nguyên trạng
  (TT 04/2022, BHTG 125tr, output guard chống cam kết).
- Ràng buộc đầu ra: chỉ gợi ý sản phẩm **trong catalog của ngân hàng đối tác**; mỗi gợi ý kèm
  lãi suất niêm yết + effective_date + citation quy định; bắt buộc disclosure "dữ liệu khách
  quan, không phải khuyến nghị đầu tư"; kèm hành động chuyển RM (UR-16).
- Kiểm thử: không đăng nhập/không opt-in → không truy cập background (kiểm chứng ở Hub log);
  gợi ý nằm ngoài catalog = fail; thiếu disclosure = fail.

**FR-15 · Doanh nghiệp đặt tiền gửi qua ERP** — Thấp, B2B+
- Luồng theo BPMN mục 10.3 tài liệu BA: ERP → Hub (xác thực) → advisory (tái dùng FR-01/02/03,
  guard FR-11) → BPM phê duyệt theo hạn mức → core banking hạch toán → CRM ghi nhận → chứng
  từ về ERP. Chatbot không bao giờ tự hạch toán — mọi giao dịch qua phê duyệt đối tác.

---

## 4. Yêu cầu giao diện ngoài

| Giao diện | Đặc tả |
|---|---|
| **UI người dùng** | Web chat (Next.js 14): MessageList/Bubble, SourcePill (citation), ConflictNotice, RateTableCard, InterestCalculatorCard, QuickReplies, TypingIndicator; đăng nhập + màn quản trị riêng |
| **API** | REST `/api/v1/*`: chat, search/retrieval, rates/compare, documents, ingestion, embeddings, health (contract: `doc/API_CONTRACT.md`) |
| **LLM** | DeepSeek qua HTTPS API; timeout + retry; adapter thay được model |
| **Embedding** | BGE-M3 self-host, vector 1024 chiều |
| **Nguồn lãi suất** | 4 cơ chế thu thập đã kiểm chứng (API BIDV, RSC VietinBank, hidden API VCB, PDF Techcombank) |
| **Hub (B2B+)** | REST/gRPC theo contract Hub; chuẩn tham chiếu Temenos open APIs |

## 5. Yêu cầu phi chức năng

> Kế thừa 7 mục NFR của tài liệu BA, lượng hóa để kiểm thử được:

| ID | Hạng mục | Yêu cầu đo được |
|---|---|---|
| NFR-01 | Chính xác số liệu | 100% số lãi suất hiển thị khớp Rate DB (fact-check FR-08) |
| NFR-02 | Chính xác truy hồi | Precision@5 ≥ 85%; Answer Faithfulness ≥ 90%; Conflict accuracy ≥ 80% |
| NFR-03 | Hiệu năng | P95 ≤ 5s/câu hỏi; ingest ≥ 50 docs/giờ |
| NFR-04 | Khả dụng | B2C 24/7; LLM gián đoạn → thông điệp degrade tử tế, không lỗi trắng trang |
| NFR-05 | Bảo mật & riêng tư | Không thu thập dữ liệu tài chính cá nhân khi chưa đồng ý; JWT cho B2B; secrets qua env; chặn injection/PII (FR-11) |
| NFR-06 | Tuân thủ | Không khuyến nghị đầu tư cá nhân hóa; mọi câu trả lời ghi nguồn + thời điểm dữ liệu |
| NFR-07 | Kiểm toán | Mọi câu trả lời truy vết được về văn bản/Điều hoặc bản ghi Rate DB; log pipeline theo phiên |
| NFR-08 | Mở rộng | Thêm ngân hàng/domain mới không đổi schema gốc; thêm năng lực KI = thêm processor; thay vector store/LLM qua adapter |
| NFR-09 | Chất lượng mã | CI bắt buộc Ruff + MyPy + Pytest xanh trước merge |

## 6. Yêu cầu dữ liệu

| Kho | Nội dung | Ghi chú |
|---|---|---|
| `document_chunks` | Lớp A/B — 1 chunk = 1 Điều; metadata: doc_class, khoan/diem (nullable), doi_tuong_ap_dung, bank, authority_level, effective/expired, status | Chunking không cắt đôi Điều |
| `document_relations` | Cạnh đồ thị: supersedes/amends/huong_dan/cross_reference/CONFLICTS_WITH + confidence + source/target_chunk_id | Curate bởi người, có nguồn gốc từ chính văn bản khi có thể |
| `bank_products` (Rate DB) | Lớp C: bank, product, term, segment, channel, rate_value, effective_date; unique key chống trùng khi re-ingest | Truy vấn SQL, không semantic search cho so sánh số |
| Log/thống kê | structlog + statistics per-response | Phục vụ NFR-07, FR-13 |

## 7. Ma trận truy vết

| FR | UR (URD) | Thành phần hiện thực | Kiểm thử |
|---|---|---|---|
| FR-01 | UR-01/02/04/12 | chat_service, rag_service, generation/ | test_chat_service_wave4, test_prompt_builder |
| FR-02 | UR-03 | api/search `/rates/compare`, bank_product_store | test KI/pipeline + kiểm DB |
| FR-03 | UR-07 | metadata filter, intent routing (rag_service) | test retrieval filter |
| FR-04/05 | UR-03 | scripts/ingest_bank_rates + scheduler (G2) | — (G2) |
| FR-06 | UR-09 | JWT + Lớp B (G3) | — (G3) |
| FR-07/10 | UR-10 | VersionResolution/TimelineProcessor | test_ki_pipeline_processors |
| FR-08 | UR-02/05 | formatter/fact-check + SQL path | test_response_formatter |
| FR-09 | UR-13 | ConflictDetectionProcessor + ConflictNotice | test_ki_pipeline_processors |
| FR-11 | UR-05/06 | guardrails/rules, guardrail_service | test_guardrails |
| FR-12 | UR-14 | scripts/ingest, document_loader, api ingestion | test_document_relation |
| FR-13 | UR-15 | structlog + statistics | test_main |
| FR-14 | UR-11/16 | Hub + ProcessOwnerResolver (B2B+) | contract tests (B2B+) |
| FR-15 | UR-08 | Hub + BPM + core banking (B2B+) | e2e partner sandbox (B2B+) |
| FR-17 | UR-17 | Hub + ProductMatching processor (B2B+) | contract test Hub + kiểm catalog/disclosure |
| FR-16 | UR-01/04 | RelationshipExpansion + AuthorityRanking | test_ki_pipeline_processors |

## 8. Tiêu chí nghiệm thu tổng thể (Definition of Done theo giai đoạn)

- **G1 (MVP)**: FR-01/02/03/08/11/12/16 pass toàn bộ kiểm thử nêu trên; NFR-01/03/05/06 đạt;
  demo 5 câu FAQ chuẩn không mất citation, không conflict giả, không số liệu lệch DB.
- **G2**: FR-04/05/07/09/10/13 + NFR-02 đo trên bộ evaluation chuẩn.
- **G3**: FR-06 + phân quyền đối tác + NFR-07 mức kiểm toán đầy đủ.
- **B2B+**: FR-14/15 với contract test Hub và e2e sandbox đối tác.
