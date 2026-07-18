# Test Plan: 7 chức năng Knowledge Intelligence (KI) Pipeline

## Bối cảnh

Cả 7 chức năng dưới đây là các `KnowledgeProcessor` chạy tuần tự trong
`KnowledgePipeline` (`backend/app/services/document_relation_service.py`),
được `DocumentRelationService.process(query, results)` gọi sau bước hybrid
retrieval và trước khi build prompt cho LLM (xem `chat_service.py` bước 3).
Mỗi processor nhận vào một `KnowledgeContext` dùng chung và sửa nó tại chỗ
(`ranked_chunks`, `document_map`, `relationships`, `citations`, `conflicts`,
`timeline`, `metadata`, `statistics`), theo thứ tự:

```
AuthorityRankingProcessor → RelationshipExpansionProcessor →
VersionResolutionProcessor → ConflictDetectionProcessor →
DuplicateRemovalProcessor → CitationProcessor → TimelineProcessor →
ContextBuilderProcessor
```

File test: `backend/tests/test_ki_pipeline_processors.py` (31 test case, chạy
độc lập với DB — không cần Postgres/embedding-service, chỉ mock/monkeypatch
tối thiểu). Chạy: `cd backend && python -m pytest tests/test_ki_pipeline_processors.py -v`.

Quy ước đặt tên trong bảng bên dưới: **Class test** = class Python test
tương ứng trong file test; **Case** = tên hàm test.

---

## 1. Authority Ranking — `AuthorityRankingProcessor`

**Mục đích:** ưu tiên văn bản có giá trị pháp lý cao hơn (Luật > Thông tư >
Quyết định > SOP nội bộ) bằng cách trộn điểm retrieval gốc với điểm authority
tra theo `authority_level` của văn bản chứa chunk đó.

**Công thức:** `score' = (1 - weight) * score + weight * authority_score`,
với bảng điểm mặc định `NATIONAL_LAW=1.0, NHNN_CIRCULAR=0.8, NHNN_DECISION=0.7,
INTERNAL_POLICY=0.5, DEPARTMENT_SOP=0.3, FAQ=0.1, UNKNOWN=0.0`.

**Class test:** `TestAuthorityRanking`

| Case | Kiểm tra |
|---|---|
| `test_higher_authority_ranks_first_when_raw_scores_tie` | 2 chunk cùng điểm retrieval gốc, khác authority_level → sau xử lý, chunk thuộc văn bản authority cao hơn phải đứng đầu (re-sort đúng) |
| `test_score_blend_formula_is_exact` | Công thức trộn điểm tính đúng theo weight, `metadata["authority_score"]`/`["authority_level"]` được gắn đúng |
| `test_chunk_with_no_matching_document_gets_zero_authority` | Chunk có `document_id` không có trong `document_map` (dữ liệu thiếu/lỗi) → `authority_score=0.0`, không crash, không gắn field `authority_level` |
| `test_custom_authority_scores_override_default` | Cho phép truyền bảng điểm authority tùy chỉnh (không bị khoá cứng vào bảng mặc định) |
| `test_sets_statistics_flag` | `statistics["authority_ranking_applied"] is True` sau khi chạy |

---

## 2. Relationship Expansion — `RelationshipExpansionProcessor`

**Mục đích:** không chỉ dừng ở top-k retrieval — tự động kéo thêm các văn bản
**liên quan** (qua `document_relations`: AMENDS/REPLACES/REFERENCES/...) vào
`document_map` dù chúng không nằm trong kết quả retrieval ban đầu, để các
processor sau (Version Resolver, Conflict Detection, Timeline) có đủ ngữ cảnh.

**Cách mở rộng:** 1 hop "miễn phí" ngay từ `context.relationships` ban đầu
(quan hệ của các doc đã retrieve), sau đó lặp tối đa `max_depth` vòng, mỗi
vòng truy vấn quan hệ của "frontier" (các doc mới phát hiện ở vòng trước) để
tìm thêm 1 hop nữa — dừng sớm nếu frontier rỗng hoặc đã chạm `max_relations`.

**Class test:** `TestRelationshipExpansion` (mock DB bằng cách monkeypatch
thẳng `_fetch_relations`/`_fetch_documents` — 2 hàm này chỉ là SELECT thuần,
giá trị test nằm ở logic frontier/depth/cap, không phải ở SQL)

| Case | Kiểm tra |
|---|---|
| `test_expands_to_related_document_not_in_top_k` | Doc B chỉ liên quan qua quan hệ AMENDS với doc A (đã retrieve) → B phải được kéo vào `document_map` dù không nằm trong top-k |
| `test_multi_hop_expansion_within_max_depth` | Chuỗi A→B→C→D; `max_depth=1` → kéo được tới C (qua quan hệ của B) nhưng KHÔNG tới D (cần thêm 1 vòng nữa) — xác nhận cận `max_depth` có tác dụng thật |
| `test_max_relations_cap_stops_expansion` | `max_relations` đã chạm ngưỡng → vòng lặp mở rộng dừng ngay (`expansion_count=0`), dù B vẫn được thêm ở bước hop miễn phí ban đầu (không bị cap) |
| `test_no_relationships_means_no_expansion` | Không có quan hệ nào → không mở rộng, `document_map` giữ nguyên |

---

## 3. Version Resolver — `VersionResolutionProcessor`

**Mục đích:** chọn đúng phiên bản còn hiệu lực/mới nhất — chunk thuộc văn bản
đã bị thay thế (target của quan hệ `REPLACES`) bị đánh dấu `superseded=True`
và giảm điểm theo `superseded_penalty`, để văn bản mới nổi lên trên.

**Class test:** `TestVersionResolver`

| Case | Kiểm tra |
|---|---|
| `test_chunk_from_superseded_document_is_penalized` | Doc bị REPLACES → `metadata["superseded"]=True`, `version_note` đúng câu, `score` nhân đúng hệ số phạt |
| `test_chunk_from_current_document_is_untouched` | Doc không bị thay thế → `superseded=False`, điểm không đổi |
| `test_resorts_after_penalty_changes_order` | Sau khi phạt điểm, thứ tự `ranked_chunks` được sắp lại đúng (văn bản mới lên trên văn bản cũ) |
| `test_superseded_count_statistic` | `statistics["superseded_count"]` đếm đúng số văn bản bị thay thế (theo `target_doc_id`, không theo số chunk) |
| `test_version_note_added_to_context_metadata` | `context.metadata["version_notes"]` chứa đúng câu ghi chú kèm tên văn bản |

---

## 4. Amendment Resolver — `DocumentRelationService.apply_amendment`

**Mục đích:** khi nhiều chunk cùng thuộc 1 văn bản được retrieve (thường xảy
ra vì mỗi Điều/Khoản là 1 chunk riêng), chỉ giữ lại chunk đại diện có điểm cao
nhất — **không bao giờ** loại 2 chunk khác `document_id` (bug đã sửa trong
`Corpus_Ingestion_Ontology_Plan.md`: dedup cũ theo `title` từng làm mất Điều).

Case cơ bản (2 chunk 1 doc, 2 chunk 2 doc khác nhau) đã có sẵn ở
`backend/tests/test_document_relation.py`. File mới bổ sung thêm case biên:

**Class test:** `TestAmendmentResolver`

| Case | Kiểm tra |
|---|---|
| `test_empty_input_returns_empty` | Input rỗng → output rỗng, không lỗi |
| `test_three_chunks_same_document_keeps_only_max_score` | 3 chunk cùng doc, điểm khác nhau → chỉ giữ đúng 1 chunk có điểm cao nhất (không phải chunk gặp cuối cùng) |
| `test_tie_break_keeps_first_seen_chunk` | 2 chunk cùng doc, điểm bằng nhau → giữ chunk gặp trước (do so sánh dùng `>` chứ không phải `>=`) — hành vi xác định, không phụ thuộc thứ tự ngẫu nhiên |

---

## 5. Conflict Detection — `ConflictDetectionProcessor`

**Mục đích:** phát hiện mâu thuẫn giữa các nguồn — nhưng **chỉ** dựa trên
quan hệ `CONFLICTS_WITH` tường minh trong `document_relations`, KHÔNG dựa vào
heuristic "trùng tiêu đề Điều" (đó là `detect_conflicts()`, một helper khác
**không được wire vào pipeline thật** — xem comment trong
`document_relation_service.py` dòng ~596 và case
`test_document_relation.py::test_detect_conflicts_*`). Đây là điểm quan trọng
đã được xác minh khi implement `doc/Corpus_Ingestion_Ontology_Plan.md` Phase E:
corpus có rất nhiều Điều trùng tiêu đề giữa các văn bản không liên quan
("Điều 1. Phạm vi điều chỉnh"), nếu dùng heuristc trùng tiêu đề sẽ báo
conflict giả tràn lan.

**Class test:** `TestConflictDetection`

| Case | Kiểm tra |
|---|---|
| `test_disabled_processor_reports_zero_and_skips` | `enabled=False` → `conflict_count=0`, **không đụng vào** `context.conflicts` hiện có (early return đúng) |
| `test_flags_conflict_when_related_doc_is_retrieved` | Quan hệ `CONFLICTS_WITH` giữa 2 doc, 1 trong 2 đang được retrieve → conflict được flag, `metadata["has_conflicts"]=True` |
| `test_no_conflict_when_neither_document_retrieved` | Quan hệ `CONFLICTS_WITH` tồn tại nhưng không liên quan gì tới các chunk đang trả lời → không báo conflict giả |
| `test_non_conflict_relation_types_are_ignored` | Quan hệ khác loại (vd `AMENDS`) giữa 2 doc đã retrieve → không bị hiểu nhầm thành conflict |

---

## 6. Citation Builder — `CitationProcessor`

**Mục đích:** tạo trích dẫn chính xác đến Điều/Khoản/Điểm cho từng chunk
được dùng trong câu trả lời — ghép `section_number` (vd "Khoản 2") +
`section_title` (vd "Điều 3.") + metadata văn bản (`doc_number`,
`authority_level`, `version`, `effective_date`).

**Class test:** `TestCitationBuilder`

| Case | Kiểm tra |
|---|---|
| `test_builds_citation_with_correct_fields` | Mọi field của `Citation` (doc_number, section_number, section_title, authority_level, version, effective_date, chunk_index) map đúng từ `Document` + `SearchResult` |
| `test_respects_max_citations_cap` | Chỉ build đúng `max_citations` citation đầu tiên (theo thứ tự `ranked_chunks`, đã qua Authority Ranking + Version Resolver) |
| `test_content_preview_truncated_to_200_chars` | `content_preview` cắt đúng 200 ký tự cho nội dung dài |
| `test_missing_document_falls_back_to_defaults` | Chunk có `document_id` không có trong `document_map` → dùng giá trị mặc định an toàn ("Unknown", `authority_level="UNKNOWN"`, `version=1`), không crash |
| `test_disabled_processor_does_not_touch_citations` | `enabled=False` → `context.citations` giữ nguyên |

---

## 7. Timeline Builder — `TimelineProcessor`

**Mục đích:** dựng lịch sử thay đổi văn bản (chuỗi các bản REPLACES nhau) để
hiển thị "văn bản này đã qua mấy lần sửa đổi, bản nào là bản hiện hành".

**Thuật toán:** dựng map `replaces_of[bản_cũ] = bản_mới` từ quan hệ
`REPLACES`, tìm điểm bắt đầu là bản **không bị thay thế bởi ai nhưng có** bị
người khác thay thế (`target_ids - source_ids`), rồi đi dọc chuỗi tới bản mới
nhất (`is_current=True` khi bản đó không còn nằm trong `target_ids`).

**Class test:** `TestTimelineBuilder`

| Case | Kiểm tra |
|---|---|
| `test_builds_oldest_to_current_chain` | Chuỗi 3 bản V1→V2→V3 (V2 thay V1, V3 thay V2) → timeline đúng thứ tự cũ→mới, `is_current` chỉ đúng ở bản cuối |
| `test_no_replaces_relations_gives_empty_timeline` | Không có quan hệ REPLACES nào → timeline rỗng (early return, không lỗi) |
| `test_disabled_processor_does_not_build_timeline` | `enabled=False` → không build timeline dù có quan hệ REPLACES |
| `test_circular_replaces_relation_does_not_crash` | Dữ liệu lỗi tạo vòng lặp (A thay B, B thay A) → không tìm được điểm bắt đầu hợp lệ, **không crash**, timeline rỗng, chỉ log warning (`timeline_circular_reference_detected`) |
| `test_missing_document_falls_back_to_id_string` | Document không có trong `document_map` → `document_title` fallback về `str(document_id)` thay vì lỗi |

---

## Phạm vi KHÔNG cover trong bộ test này (out of scope)

- `DuplicateRemovalProcessor` — không nằm trong 7 chức năng được yêu cầu, logic đơn giản (dedup theo `chunk_id`), rủi ro thấp.
- `ContextBuilderProcessor` — chỉ cắt/gom kết quả cuối, không có logic nghiệp vụ cần test riêng.
- Chất lượng retrieval/ranking của BM25+Vector (không thuộc KI pipeline, đã có `HybridRetriever` riêng).
- Test tích hợp qua API thật (`POST /api/v1/chat`) — đã verify thủ công khi triển khai Lớp C/Khoản-Điểm (xem lịch sử hội thoại), không đưa vào bộ test tự động vì cần DB + embedding-service sống.

## Chạy toàn bộ test

```bash
cd backend
python -m pytest tests/test_ki_pipeline_processors.py -v   # chỉ 7 chức năng KI
python -m pytest tests/ -q                                  # toàn bộ test suite (91 case)
```
