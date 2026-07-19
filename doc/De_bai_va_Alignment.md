# Alignment với Đề bài — Advanced RAG cho kho văn bản ngân hàng

> **Đề bài (nguyên văn):** "An advanced Retrieval-Augmented Generation (RAG) system that
> enables employees and customers to search across the bank's entire document repository
> using natural language. The system covers internal policies, regulations, circulars,
> operating procedures, contract templates, and more. What sets this solution apart is its
> ability to handle the complexities of real-world banking documentation: Cross-references
> · Amendments · Partial supersession · Conflicting regulations."

Cập nhật: 2026-07-19. Tài liệu này map **từng câu của đề bài** sang hiện trạng hệ thống,
kèm bằng chứng (file/code/test) và kịch bản demo tương ứng.

---

## 1. Ma trận alignment từng yêu cầu

| # | Yêu cầu trong đề bài | Hiện trạng | Bằng chứng | Demo |
|---|---|---|---|---|
| 1 | **RAG system** — retrieval-augmented, không phải FAQ bot | ✅ Hybrid retrieval (BM25 + pgvector/BGE-M3) + metadata filter trước similarity + LLM grounded chỉ từ context | `rag_service.py`, `vector_store.py` | Câu hỏi tự do ngoài kịch bản vẫn trả lời kèm nguồn |
| 2 | **Employees AND customers** | ✅ 2 luồng: GDV/compliance (trích dẫn Điều-level, timeline, conflict) và khách hàng (ngôn ngữ dễ hiểu, RateTable, Calculator) | URD 6 user classes; frontend components | 1 câu hỏi, 2 kiểu trình bày |
| 3 | **Entire document repository** — policies, regulations, circulars, procedures, templates | ✅ Ontology 3 lớp: Lớp A pháp lý (Luật/NĐ/TT — 14 văn bản, 474 Điều), Lớp B nội bộ (quy định ngân hàng, gắn `bank`), Lớp C số liệu (`bank_products`) | `Giai_thich_co_che_Ontology.md`, `data/raw/` | Corpus thật đã ingest |
| 4 | **Natural language (tiếng Việt)** | ✅ BGE-M3 (tối ưu tiếng Việt) + intent routing keyword (bank, cá nhân/DN, so sánh) | `rag_service.py:_infer_filters` | Hỏi bằng văn nói: "rút sớm có mất lãi không?" |
| 5 | **Cross-references** — follow & synthesize related docs | ✅ `RelationshipExpansionProcessor`: BFS trên `document_relations` (REFERENCES/IMPLEMENTS/AMENDS/SUPPLEMENTS), max 2 hops, cap 20, score decay | `document_relation_service.py:227` + test | Hỏi BHTG → sources đủ chuỗi Luật 06/2012 → NĐ 68/2013 → TT 24/2014 |
| 6 | **Amendments** — always latest effective version | ✅ `VersionResolutionProcessor`: REPLACES → penalty ×0.5 + version note; filter `exclude_expired` tầng SQL; `TimelineProcessor` dựng chuỗi phiên bản | `document_relation_service.py:306,459` + test | TT 48/2018 vs 48/2024: trả lời theo 2024, kèm note + timeline |
| 7 | **Partial supersession** — exclude superseded clauses only | ✅ Quan hệ curate ở mức chunk (`source/target_chunk_id` trong metadata_extra); `apply_partial_supersession` loại đúng Điều/Khoản bị thay, giữ phần còn hiệu lực; chunking 1 Điều = 1 chunk | `document_relation_service.py:617` | Rút trước hạn: điều khoản cũ bị loại, trả theo TT 04/2022, các Điều khác của văn bản cũ vẫn dùng được |
| 8 | **Conflicting regulations** — detect + alert users | ✅ `ConflictDetectionProcessor`: CONFLICTS_WITH chunk-scoped (logic OR chống false positive), trả `conflicts[]` 2 phía + confidence; UI `ConflictNotice`; authority ranking phân giải Luật > TT > QĐ > nội bộ > FAQ | `document_relation_service.py:337`, `ConflictNotice.tsx` + test | Câu chạm cặp conflict → cảnh báo 2 phía trên UI |

**Kết luận alignment: 8/8 yêu cầu của đề bài đã hiện thực và chạy end-to-end**, có test
(`test_ki_pipeline_processors.py` ~740 dòng cover đúng 4 năng lực khó).

## 2. Phần vượt đề bài (điểm cộng khi chấm)

| Năng lực | Giá trị |
|---|---|
| Guardrails 3 tầng (input/retrieval/output) | Đề bài ngầm định đúng-và-an-toàn; ta làm tường minh: chặn injection/PII, từ chối khi thiếu context (chống hallucination), lọc cam kết rủi ro |
| Lớp C — so sánh lãi suất 5 ngân hàng bằng SQL | "Số liệu không đi qua embedding" — LLM không bao giờ đoán số; dữ liệu crawl từ nguồn chính thức đã xác thực |
| Authority ranking | Đúng nguyên tắc áp dụng pháp luật khi nguồn vênh nhau |
| Mở rộng: tư vấn sản phẩm theo background KH | Consent-first; background từ core Temenos / CRM / SAHA qua Central Integration Hub (`Kha_nang_mo_rong_Extensibility.md` mục 3) |
| Chi phí vận hành | ~20đ/câu trả lời, ~3 triệu đ/tháng ở quy mô MVP (BA doc mục 11) |
| Kỹ thuật | Clean Architecture, 1 PostgreSQL duy nhất, CI (Ruff/MyPy/Pytest), 9 test files, Docker/GCP |

## 3. Kịch bản demo 5 câu (bám đề bài, mỗi câu 1 năng lực)

1. **RAG + citation**: "Người gửi tiền được bảo hiểm tối đa bao nhiêu?" → trả lời + citation QĐ 32/2021 + Luật BHTG.
2. **Cross-references**: "Bảo hiểm tiền gửi áp dụng cho loại tiền gửi nào?" → sources 3 tầng văn bản (Luật → NĐ → TT).
3. **Amendments**: "Quy định lãi suất tiền gửi hiện hành theo thông tư nào?" → TT 48/2024 + version note "48/2018 đã bị thay thế" + timeline.
4. **Partial supersession**: "Rút một phần sổ tiết kiệm trước hạn, phần còn lại tính lãi thế nào?" → đúng TT 04/2022, điều khoản cũ không xuất hiện.
5. **Conflict**: câu chạm cặp CONFLICTS_WITH đã curate → ConflictNotice hiện cả 2 phía + confidence.

Bonus (nếu còn thời gian): "Ngân hàng nào lãi suất 12 tháng cao nhất?" (SQL Lớp C) và 1 câu
prompt injection để show guardrail.
