# VAIC-Nextlevel
# TECH STACK
## Advanced RAG Knowledge Base — Tiền gửi (SHB Bank)

*Cập nhật ngày 17/07/2026 — Đã chốt theo lựa chọn của team*

| Thành phần | Lựa chọn | Lý do |
|---|---|---|
| Ngôn ngữ chính (backend/RAG) | Python | Hệ sinh thái RAG mạnh nhất, tốc độ code nhanh, phù hợp 48h |
| RAG framework | LlamaIndex | Thiên về retrieval/RAG hơn LangChain, ít boilerplate hơn cho use case này |
| Embedding model | BAAI/bge-m3 (local, miễn phí) hoặc embedding API đi kèm nhà cung cấp LLM | bge-m3 hỗ trợ tiếng Việt tốt, không tốn phí, chạy local nhanh |
| Vector DB | Supabase |  |
| LLM sinh câu trả lời | DeepSeek V4 | Lựa chọn của team — cần chuẩn bị sẵn API key/quota trước giờ H0, và test sớm khả năng xử lý tiếng Việt + function calling (nếu cần) ngay từ H2-H10 để phát hiện sớm nếu chất lượng không đạt |
| Lưu quan hệ văn bản & metadata | SQLite hoặc file JSON | Đơn giản, đủ dùng cho quy mô dữ liệu nhỏ, không cần graph DB |
| Backend API | FastAPI | Nhanh, tự sinh docs API, dễ để Dương tích hợp UI |
| Giao diện demo | React/Next.js | Lựa chọn của team — đẹp và tuỳ biến hơn Streamlit, nhưng tốn thời gian dựng hơn trong 48h, cần Dương ưu tiên làm sớm và giữ scope UI tối giản |
| Đóng gói | Docker + docker-compose | Chạy ổn định trên máy khác, đúng phần việc của Phượng |
| Quản lý mã nguồn | GitHub, nhánh theo từng người/feature | Tránh xung đột khi nhiều người code song song |

## Lưu ý khi triển khai trong 48h

- Với React/Next.js thay vì Streamlit, nên rút gọn scope UI xuống còn 1 màn hình chat + khu vực hiển thị trích dẫn/cảnh báo — không làm thêm trang phụ, không làm animation/theme phức tạp, để bù lại thời gian dựng frontend từ đầu (ước tính tốn thêm 3-4 giờ so với Streamlit).
- Nên setup và test DeepSeek V4 (API key, quota, khả năng xử lý tiếng Việt) ngay trong H2-H10 — đây là điểm rủi ro cần phát hiện sớm nếu chất lượng không đạt, để còn thời gian đổi phương án.
- Ưu tiên toàn bộ stack có thể chạy local hoặc setup trong vài phút (Chroma, SQLite) để không mất thời gian 48h vào việc dựng hạ tầng.
