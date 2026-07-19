# So sánh chi tiết 4 tiêu chí Knowledge Intelligence — SHB RAG Chatbot vs Chatbot 4 ngân hàng

> Tài liệu bổ sung cho `So_sanh_chatbot_5_ngan_hang.md`, đi sâu vào 4 tiêu chí cốt lõi của tầng
> Knowledge Intelligence (KI). Mô tả cơ chế dựa trên implementation thực tế trong
> `backend/app/services/document_relation_service.py` (KI pipeline 8 processors).
> Đối thủ so sánh: VCB Digibot (FPT.AI), BIDV Chatbot (iBank/Messenger), VietinBank Chatbot AI, Techcombank.

Cập nhật: 2026-07-19.

---

## Vì sao 4 tiêu chí này quan trọng?

Văn bản pháp lý ngân hàng (Thông tư NHNN, Luật, Nghị định) không tồn tại độc lập — chúng
**tham chiếu lẫn nhau, sửa đổi nhau, thay thế nhau từng phần, và đôi khi mâu thuẫn nhau**.
Một câu trả lời đúng về nghiệp vụ tiền gửi bắt buộc phải xử lý được 4 tình huống này.
Chatbot FAQ/intent-based của 4 ngân hàng **không có khái niệm "văn bản"** trong kiến trúc —
chúng chỉ match câu hỏi vào intent tree và trả câu soạn sẵn, nên cả 4 tiêu chí đều nằm ngoài
khả năng của chúng về mặt cấu trúc, không phải chỉ là "chưa làm".

---

## Tiêu chí 1 — Cross-references (Tham chiếu chéo)

**The system automatically follows and synthesizes information from related documents, so users
get complete and context-aware answers.**

### Vấn đề thực tế

Thông tư thường quy định "theo quy định tại Luật Các tổ chức tín dụng" hoặc "hướng dẫn thi hành
Nghị định X". Nếu chỉ retrieve đúng văn bản chứa keyword, câu trả lời sẽ thiếu ngữ cảnh từ các
văn bản được tham chiếu — user nhận câu trả lời đúng một nửa.

### Cơ chế của hệ thống (RelationshipExpansionProcessor)

- Sau khi hybrid retrieval trả về top-k chunks, hệ thống lấy các `document_id` và **duyệt đồ thị
  quan hệ** trong bảng `document_relations` bằng BFS: `max_depth = 2 hops`, giới hạn
  `max_relations = 20` để kiểm soát context size.
- Các relation type được theo: `REFERENCES`, `IMPLEMENTS`, `AMENDS`, `SUPPLEMENTS` — mỗi quan hệ
  kéo thêm document liên quan vào `document_map`, làm giàu context trước khi đưa vào LLM.
- Kết quả: câu trả lời **tổng hợp (synthesize) từ nhiều văn bản liên quan**, không chỉ văn bản
  match keyword.

### Ví dụ

> **User hỏi:** "Bảo hiểm tiền gửi áp dụng cho những loại tiền gửi nào?"
>
> - **Bot 4 ngân hàng:** trả câu FAQ soạn sẵn (nếu có intent), không dẫn văn bản, không biết đến
>   quan hệ giữa Luật BHTG và các văn bản hướng dẫn.
> - **Bot của bạn:** retrieve trúng Luật BHTG 06/2012/QH13 → graph expansion tự kéo thêm
>   Nghị định 68/2013/NĐ-CP (hướng dẫn thi hành) và Thông tư 24/2014/TT-NHNN → câu trả lời tổng
>   hợp cả 3 tầng văn bản, mỗi ý kèm citation riêng.

| | Bot của bạn | Bot 4 ngân hàng |
|---|---|---|
| Hiểu quan hệ giữa các văn bản | ✅ Graph BFS 2 hops, 4 relation types | ❌ Không có khái niệm document |
| Tổng hợp đa văn bản trong 1 câu trả lời | ✅ Multi-document synthesis + citation | ❌ 1 intent = 1 câu trả lời tĩnh |
| Độ phủ khi văn bản mới được ingest | Tự động (chỉ cần khai báo relations) | Phải viết lại kịch bản tay |

---

## Tiêu chí 2 — Amendments (Văn bản sửa đổi)

**The system always applies the latest effective version of amended regulations, ensuring
responses reflect current rules.**

### Vấn đề thực tế

NHNN sửa đổi Thông tư liên tục. Ví dụ ngay trong corpus: TT 48/2018/TT-NHNN về lãi suất tiền gửi
đã được thay bằng TT 48/2024/TT-NHNN. Trả lời theo bản 2018 là **sai nghiệp vụ và rủi ro
compliance** — nhưng bản cũ vẫn nằm trong kho tài liệu và vẫn match keyword rất mạnh.

### Cơ chế của hệ thống (VersionResolutionProcessor)

- Quét các relation `REPLACES` trong context: document bị trỏ đến (target) được đánh dấu
  `superseded = True`.
- Chunk thuộc văn bản đã bị thay thế bị **phạt điểm** (`score × 0.5`) → tự động tụt xuống dưới
  bản mới trong ranking, và gắn `version_note: "Đã bị thay thế bởi văn bản mới hơn"`.
- Kết hợp `TimelineProcessor`: dựng chuỗi thay thế (TT 48/2018 → TT 48/2024) với cờ `is_current`
  cho từng bản, expose trong response của `/api/v1/chat` để UI hiển thị timeline.
- Retrieval layer còn có filter `exclude_expired=True` chặn văn bản hết hiệu lực ngay từ bước search.

### Ví dụ

> **User hỏi:** "Lãi suất tối đa với tiền gửi VND được quy định ở đâu?"
>
> - **Bot 4 ngân hàng:** không trả lời được câu hỏi mức văn bản; nếu có intent về lãi suất thì
>   trả con số hiện tại của riêng ngân hàng đó, không nói theo quy định nào.
> - **Bot của bạn:** cả TT 48/2018 và TT 48/2024 đều được retrieve (cùng chủ đề, keyword giống
>   nhau) → version resolver phát hiện quan hệ REPLACES → trả lời theo **TT 48/2024**, kèm
>   version note bản 2018 đã hết hiệu lực + timeline 2 bản cho user đối chiếu.

| | Bot của bạn | Bot 4 ngân hàng |
|---|---|---|
| Nhận biết văn bản đã bị thay thế | ✅ Relation REPLACES + score penalty 0.5 | ❌ |
| Luôn trả lời theo bản còn hiệu lực | ✅ + version note minh bạch | ⚠️ Đúng chỉ khi admin nhớ cập nhật kịch bản tay |
| Hiển thị lịch sử phiên bản | ✅ Timeline Builder trong API response | ❌ |

---

## Tiêu chí 3 — Partial supersession (Thay thế từng phần)

**When regulations are partially updated, the system excludes superseded clauses from responses,
keeping information accurate and relevant.**

### Vấn đề thực tế

Đây là tình huống khó nhất: văn bản mới **chỉ thay một số điều khoản** của văn bản cũ — phần còn
lại của văn bản cũ **vẫn còn hiệu lực**. Ví dụ kinh điển: TT 04/2022/TT-NHNN thay quy định về
rút tiền gửi trước hạn, nhưng các điều khác của thông tư bị sửa vẫn áp dụng. Nếu loại cả văn bản
cũ → mất thông tin còn hiệu lực; nếu giữ nguyên → trả lời theo điều khoản đã chết.

### Cơ chế của hệ thống

- Quan hệ thay thế được curate **ở mức chunk** chứ không chỉ mức document: relation lưu
  `source_chunk_id` / `target_chunk_id` trong `metadata_extra` — trỏ đúng đến Điều/Khoản bị thay
  (chunking theo cấu trúc Điều/Khoản của văn bản pháp lý Việt Nam).
- `apply_partial_supersession()` lọc bỏ **đúng những chunk** mang cờ `superseded` khỏi context —
  các chunk còn hiệu lực của cùng văn bản vẫn được giữ và dùng để trả lời.
- Đây là độ phân giải mà cách "xóa văn bản cũ khỏi kho" không bao giờ đạt được.

### Ví dụ

> **User hỏi:** "Rút một phần sổ tiết kiệm trước hạn thì phần còn lại tính lãi thế nào?"
>
> - **Bot 4 ngân hàng:** trả câu FAQ chung "rút trước hạn hưởng lãi không kỳ hạn" — có thể đang
>   phản ánh quy định cũ nếu kịch bản chưa được cập nhật tay.
> - **Bot của bạn:** chunk chứa quy định cũ về rút trước hạn bị exclude (superseded ở mức
>   Điều/Khoản), trả lời theo **TT 04/2022**: phần rút trước hạn hưởng lãi không kỳ hạn, **phần
>   còn lại giữ nguyên mức lãi suất đang áp dụng** — chính xác đến từng khoản, kèm citation.

| | Bot của bạn | Bot 4 ngân hàng |
|---|---|---|
| Độ phân giải thay thế | ✅ Mức Điều/Khoản (chunk-level) | ❌ Không có khái niệm điều khoản |
| Giữ lại phần văn bản cũ còn hiệu lực | ✅ Chỉ loại đúng chunk bị thay | ❌ |
| Rủi ro trả lời theo điều khoản đã chết | Thấp (tự động theo relations) | Cao (phụ thuộc cập nhật kịch bản tay) |

---

## Tiêu chí 4 — Conflicting regulations (Văn bản mâu thuẫn)

**The system detects inconsistencies between documents and alerts users, helping them avoid
confusion and compliance risks.**

### Vấn đề thực tế

Hai văn bản cùng hiệu lực có thể quy định khác nhau về cùng một vấn đề (giai đoạn chuyển tiếp,
văn bản nội bộ chưa cập nhật theo Thông tư mới...). Nhân viên tự tra cứu sẽ chỉ thấy 1 trong 2 —
và không biết mình đang đứng trên điều khoản có tranh chấp. Đây là **rủi ro compliance thật**,
không phải edge case.

### Cơ chế của hệ thống (ConflictDetectionProcessor)

- Mâu thuẫn được curate thành relation `CONFLICTS_WITH` trong `document_relations`, kèm
  `description` (mô tả mâu thuẫn) và `confidence`.
- **Scope ở mức chunk:** relation lưu `source_chunk_id`/`target_chunk_id` — cảnh báo chỉ bật khi
  **ít nhất một trong 2 chunk cụ thể** nằm trong context đang trả lời (logic OR có chủ đích:
  cảnh báo giá trị nhất chính lúc chunk "dễ hiểu nhầm" xuất hiện, kể cả khi top-k không kéo được
  chunk đối ứng). Điều này tránh false positive kiểu "2 văn bản dài tình cờ cùng được retrieve
  cho một câu hỏi không liên quan → cảnh báo mâu thuẫn dính vào mọi câu trả lời".
- Response của `/chat` trả `conflicts[]` gồm `source_title`, `target_title`, `description`,
  `confidence` → frontend render `ConflictNotice` cho user thấy **cả hai phía** của mâu thuẫn.
- Kết hợp Authority Ranking: khi mâu thuẫn giữa 2 cấp văn bản, nguồn có thẩm quyền cao hơn
  (Luật 1.0 > Thông tư 0.8 > Quyết định 0.7 > chính sách nội bộ 0.5 > SOP 0.3 > FAQ 0.1) được
  ưu tiên trong ranking — đúng nguyên tắc áp dụng pháp luật.

### Ví dụ

> **User hỏi:** "Điều kiện rút trước hạn theo quy định hiện hành?"
>
> - **Bot 4 ngân hàng:** trả 1 câu duy nhất, user không hề biết đang có 2 quy định vênh nhau.
> - **Bot của bạn:** phát hiện chunk trong context nằm trong cặp CONFLICTS_WITH → câu trả lời
>   nêu rõ nội dung theo văn bản thẩm quyền cao hơn, đồng thời hiển thị cảnh báo: *"⚠️ Điều X
>   của [văn bản A] và Điều Y của [văn bản B] có quy định không thống nhất về vấn đề này"* — kèm
>   cả 2 citation để user/compliance officer tự thẩm định.

| | Bot của bạn | Bot 4 ngân hàng |
|---|---|---|
| Phát hiện mâu thuẫn giữa văn bản | ✅ CONFLICTS_WITH, scope mức chunk | ❌ |
| Cảnh báo user + hiển thị cả 2 phía | ✅ `conflicts[]` trong API + ConflictNotice UI | ❌ |
| Phân giải theo thẩm quyền pháp lý | ✅ Authority Ranking | ❌ |
| Giá trị compliance | Chủ động phát hiện rủi ro | Im lặng — user tự chịu rủi ro |

---

## Tổng kết

| Tiêu chí | Bản chất kỹ thuật | Bot của bạn | Bot 4 ngân hàng |
|---|---|---|---|
| **Cross-references** | Graph traversal trên document relations | ✅ BFS 2 hops, multi-doc synthesis | ❌ |
| **Amendments** | Version resolution qua relation REPLACES | ✅ Score penalty + version note + timeline | ❌ |
| **Partial supersession** | Supersession ở độ phân giải Điều/Khoản | ✅ Chunk-level exclude | ❌ |
| **Conflicting regulations** | Conflict detection + alert 2 phía | ✅ Chunk-scoped CONFLICTS_WITH + authority | ❌ |

**Một câu cho slide:** Chatbot 4 ngân hàng trả lời *"câu hỏi thường gặp"*; hệ thống của bạn trả
lời *"theo đúng văn bản còn hiệu lực"* — vì nó là hệ thống duy nhất mô hình hóa được vòng đời
của văn bản pháp lý: tham chiếu, sửa đổi, thay thế từng phần, và mâu thuẫn.

**Hướng mở rộng:** cả 4 tính năng chạy trên KI pipeline dạng processor chain (`add_processor()`)
— thêm năng lực mới (vd `ProcessOwnerResolver` tra BPM "quy trình này ai phụ trách") là thêm
1 processor, không sửa engine; nguồn dữ liệu Lớp C nâng từ crawl lên Central Integration Hub
trên Temenos open APIs của SHB mà 4 tính năng này không đổi. Chi tiết + BPMN diagram:
`Kha_nang_mo_rong_Extensibility.md`.
