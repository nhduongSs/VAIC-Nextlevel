# So sánh Chatbot SHB RAG vs Chatbot 4 ngân hàng (BIDV, VietinBank, Vietcombank, Techcombank)

Cập nhật: 2026-07-19. Nguồn đối thủ: FPT.AI case study (VCB Digibot), BIDV iBank, VietinBank Chatbot AI/VoiceBot, công bố báo chí.

| Tiêu chí | Chatbot của bạn (SHB RAG) | Chatbot 4 ngân hàng | Ví dụ minh họa |
|---|---|---|---|
| **Kiến trúc lõi** | RAG: Hybrid Retrieval (BM25 + Vector/pgvector, BGE-M3) + LLM generate | Intent/FAQ-based (VCB Digibot trên FPT.AI; BIDV iBank kịch bản Q&A) | Câu hỏi ngoài kịch bản: bot họ trả "vui lòng liên hệ tổng đài", bot bạn vẫn trả lời nếu corpus có |
| **Nguồn tri thức** | Corpus văn bản pháp lý thật đã ingest (Luật, Thông tư NHNN, T&C ngân hàng) | FAQ biên soạn sẵn theo intent tree | *"Rút trước hạn tính lãi thế nào?"* → bot bạn trích đúng **TT 04/2022/TT-NHNN**, bot họ trả câu FAQ không dẫn văn bản |
| **Citation (trích nguồn)** | ✅ Theo từng chunk, ghi rõ điều/khoản, văn bản | ❌ | Mọi câu trả lời kèm nguồn: "Điều X, Thông tư Y" |
| **Version resolution** | ✅ Tự chọn bản còn hiệu lực, kèm version note | ❌ | *"Lãi suất tiền gửi theo thông tư nào?"* → detect TT 48/2018 bị TT 48/2024 thay thế, chỉ trả lời theo bản mới |
| **Conflict detection** | ✅ Mức chunk, trả về cả 2 phía + source/target title | ❌ | *"Hai văn bản quy định khác nhau, theo cái nào?"* → flag CONFLICTS_WITH, hiển thị cả 2 điều khoản |
| **Authority ranking** | ✅ Luật > Thông tư > Quyết định > nội bộ > FAQ | ❌ | Khi mâu thuẫn, ưu tiên văn bản cấp pháp lý cao hơn |
| **Document graph** | ✅ BFS 2 hops trên `document_relations` (REFERENCES, IMPLEMENTS, AMENDS...) | ❌ | Hỏi về Luật → tự kéo thêm Thông tư hướng dẫn thi hành liên quan |
| **So sánh lãi suất liên ngân hàng** | ✅ `/rates/compare`, data crawl từ nguồn chính thức 5 ngân hàng | ❌ — mỗi bot chỉ nói lãi suất của chính ngân hàng đó | *"Gửi 500tr kỳ hạn 6 tháng ngân hàng nào lãi cao nhất?"* → Techcombank 6.65% > SHB > BIDV/CTG/VCB 3.5% |
| **Anti-hallucination** | ✅ Retrieval guard: không đủ context → từ chối trả lời | N/A (không free-generate nên không hallucinate, nhưng cũng không linh hoạt) | Câu hỏi ngoài corpus → từ chối có kiểm soát thay vì bịa |
| **Guardrails** | ✅ Input guard (injection, PII, tư vấn tài chính cá nhân) + Output guard (lọc cam kết rủi ro) | Kiểm soát bằng cách không cho LLM free-generate | *"Nên rút hết tiền mua vàng không?"* → từ chối đúng compliance; prompt injection bị chặn từ input |
| **Timeline Builder** | ✅ Dựng lịch sử sửa đổi/thay thế văn bản, expose trong chat API | ❌ | Xem timeline: TT 48/2018 → TT 48/2024 |
| **Khả năng mở rộng (extensibility)** | ✅ Điểm cắm sẵn: Central Integration Hub trên Temenos open APIs → CRM, RM Workbench, Fee & Rate Mgmt, BPM; kênh SAHA/Corporate/ERP; domain mới chỉ cần ingest corpus (BPMN: `Kha_nang_mo_rong_Extensibility.md`) | ⚠️ Mở rộng = viết thêm kịch bản; lõi phụ thuộc vendor (VCB thuê FPT.AI) | DN đặt tiền gửi từ ERP: advisory của bot tái dùng 100%, orchestration qua BPM + core banking |
| **Scale thực tế** | ❌ Hackathon stage | ✅ BIDV ~65k interaction/ngày; VCB ~350k/tháng (88% query); VietinBank +VoiceBot, đa kênh | Điểm họ hơn — chủ động nói trước khi pitch |

**Thông điệp chính:** 7 tiêu chí liên tiếp bạn ✅ còn cả 4 bên ❌ chính là tầng **Knowledge Intelligence** — thứ nền tảng chatbot generic (FPT.AI, kịch bản CSKH) không replicate được. Họ hơn về scale/kênh (bài toán vận hành); bạn giải bài toán **độ tin cậy của tri thức pháp lý** — thứ họ chưa giải.
