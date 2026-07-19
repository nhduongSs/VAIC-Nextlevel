# Rubric chấm điểm — Đề bài "Advanced RAG cho kho văn bản ngân hàng"

> Thang 100 điểm, thiết kế bám đúng đề bài: phần lõi RAG là điều kiện cần, **4 năng lực xử
> lý văn bản phức tạp (cross-references, amendments, partial supersession, conflicts) chiếm
> trọng số lớn nhất** vì là "what sets this solution apart" theo nguyên văn đề bài.
> Cột cuối: tự đánh giá của nhóm kèm bằng chứng (để giám khảo verify nhanh).

Cập nhật: 2026-07-19.

## Thang mức cho mỗi tiêu chí

- **0% điểm** — Không có / chỉ nói miệng, không demo được
- **40%** — Có thiết kế/mock, demo giới hạn hoặc hoạt động không ổn định
- **70%** — Hoạt động thật trên corpus thu nhỏ, còn thiếu sót đã biết
- **100%** — Hoạt động end-to-end trên corpus thật, có test/bằng chứng kiểm chứng được

## Bảng rubric

| # | Tiêu chí | Trọng số | Câu hỏi chấm | Tự đánh giá + bằng chứng |
|---|---|---|---|---|
| **A** | **RAG lõi đúng đề bài** | **20** | | |
| A1 | Retrieval chất lượng (hybrid, không chỉ vector; filter metadata) | 8 | Câu hỏi tự nhiên ngoài kịch bản có trả đúng nguồn? BM25+vector có fusion? | 8/8 — BM25 + pgvector + filter trước similarity (`rag_service.py`) |
| A2 | Grounded generation + citation truy vết được | 8 | Mọi câu trả lời có citation Điều-level? Có chống hallucination? | 8/8 — citation bắt buộc; retrieval guard từ chối khi thiếu context |
| A3 | Phủ đa loại tài liệu, 2 đối tượng (nhân viên + khách hàng) | 4 | Corpus có policy/TT/quy trình? UI phục vụ 2 nhóm? | 3.5/4 — Lớp A 14 văn bản/474 Điều + Lớp B/C; contract templates chưa có |
| **B** | **4 năng lực khó (điểm nhấn đề bài)** | **36** | | |
| B1 | Cross-references: theo & tổng hợp văn bản liên quan | 9 | Hỏi 1 văn bản có tự kéo văn bản được dẫn chiếu? Có kiểm soát nổ context? | 9/9 — BFS 2 hops, cap 20, decay; demo chuỗi Luật→NĐ→TT |
| B2 | Amendments: luôn bản còn hiệu lực | 9 | Cặp văn bản cũ/mới cùng match keyword — trả bản nào? Có version note/timeline? | 9/9 — REPLACES penalty + note + Timeline Builder; TT 48/2018→48/2024 |
| B3 | Partial supersession: loại đúng điều khoản, giữ phần còn hiệu lực | 9 | Độ phân giải: cả văn bản hay từng Điều/Khoản? Phần chưa bị thay còn dùng được? | 8/9 — chunk-level (Điều); độ phân giải Khoản/Điểm đã thiết kế, hoãn có chủ đích |
| B4 | Conflicts: phát hiện + cảnh báo 2 phía | 9 | Có cảnh báo thật không false-positive tràn lan? User thấy cả 2 nguồn? | 8.5/9 — chunk-scoped OR logic chống conflict giả; ConflictNotice UI; corpus chưa có case conflict "tự nhiên" (dùng case curate) |
| **C** | **An toàn & tuân thủ ngân hàng** | **12** | | |
| C1 | Guardrails: injection, PII, từ chối đúng lúc | 6 | Thử prompt injection sống? Câu ngoài phạm vi bị từ chối tử tế? | 6/6 — 3 tầng guard, `test_guardrails.py` |
| C2 | Compliance đầu ra: không cam kết, không tư vấn đầu tư, minh bạch nguồn | 6 | Output có lọc "chắc chắn lãi"? Số liệu có ngày hiệu lực? | 6/6 — output guard + fact-check số liệu qua SQL |
| **D** | **Chất lượng kỹ thuật** | **12** | | |
| D1 | Kiến trúc & code (clean, test, CI) | 6 | Có test cho phần khó nhất? CI chạy thật? | 6/6 — 9 test files (KI ~740 dòng), CI Ruff/MyPy/Pytest |
| D2 | Vận hành: chi phí, hiệu năng, observability | 6 | P95? Chi phí/câu? Log truy vết pipeline? | 5.5/6 — ~20đ/câu, ~3tr/tháng MVP, structlog per-processor; chưa có dashboard metrics |
| **E** | **Demo & trải nghiệm** | **10** | | |
| E1 | Demo live 4 năng lực trên corpus thật | 6 | 5 câu demo có chạy sống không, hay video? | Kịch bản 5 câu trong `De_bai_va_Alignment.md` mục 3 |
| E2 | UX: citation click được, cảnh báo trực quan, bảng số liệu | 4 | SourcePill/ConflictNotice/RateTable có thật? | 4/4 — components thật trong `frontend/components/chat/` |
| **F** | **Tầm nhìn & khả năng mở rộng** | **10** | | |
| F1 | Mở rộng có căn cứ vào hệ thống ngân hàng thật | 6 | Điểm cắm cụ thể hay chỉ nói "sẽ tích hợp"? | 6/6 — Hub → core Temenos/CRM/SAHA (SHB đã công bố dùng Temenos open APIs); use case tư vấn theo background KH |
| F2 | Thuyết trình: rõ, đúng giờ, trả lời Q&A | 4 | Structure bám đề bài? Trả lời được câu hỏi sâu về cơ chế? | Deck 12 slides bám đề bài (file đi kèm) |
| | **Tổng** | **100** | | **Tự chấm: ~93/100** |

## Ghi chú cho giám khảo (điểm trừ phổ biến nên soi)

1. **"Amendments" giả**: nhiều đội chỉ xóa văn bản cũ khỏi corpus — hãy hỏi *"nếu bản cũ vẫn
   trong kho thì sao?"*. Hệ thống đúng phải resolve bằng quan hệ, không bằng xóa dữ liệu.
2. **"Partial supersession" giả**: loại cả văn bản = mất phần còn hiệu lực. Hỏi: *"Điều X
   chưa bị thay của văn bản cũ còn trả lời được không?"*
3. **Conflict detection tràn**: so text tự do sẽ báo mâu thuẫn giả khắp nơi (2 văn bản nào
   chẳng có "Điều 1"). Hỏi cơ chế chống false positive.
4. **Cross-reference nổ context**: kéo nguyên văn bản 210 Điều vào prompt = phá chất lượng.
   Hỏi giới hạn hops/cap/decay.
5. **Số liệu qua embedding**: nếu lãi suất được trả lời từ vector search — hỏi *"làm sao
   chắc con số không bị LLM đọc nhầm?"*
