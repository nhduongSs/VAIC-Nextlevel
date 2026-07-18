# BRIEF CÔNG VIỆC — SPRINT 48 GIỜ
## Advanced RAG Knowledge Base — Tiền gửi (SHB Bank)

*Cập nhật ngày 17/07/2026 — Phân công theo nhân sự thật của team*

## 1. Tổng quan dự án

Xây dựng hệ thống RAG chuyên biệt cho nghiệp vụ tiền gửi tại SHB, trả lời câu hỏi bằng ngôn ngữ tự nhiên về lãi suất, điều kiện, quy trình mở/tất toán sổ tiết kiệm — luôn theo văn bản có hiệu lực mới nhất, tổng hợp thông tin liên quan, và cảnh báo khi quy định mâu thuẫn.

## 2. Nguyên tắc khi chỉ có 48 giờ

- MVP-first: ưu tiên demo đúng và rõ 4 thách thức kỹ thuật (cross-reference, amendment, partial supersession, conflict) hơn là độ phủ dữ liệu rộng.
- Dùng thư viện có sẵn (LangChain/LlamaIndex + Chroma/FAISS) cho retrieval, không tự viết pipeline từ đầu.
- Quan hệ văn bản dùng file JSON/dict đơn giản, không cần graph DB chuyên dụng.
- Giao diện demo ưu tiên chạy đúng hơn đẹp.
- CI/CD rút gọn còn Docker đóng gói + health-check, không cần pipeline phức tạp.
- Các track chạy song song ngay từ giờ đầu, không làm tuần tự.

## 3. Phân công nhân sự chi tiết

### Dương — Teamlead: codebase + UI/UX + hỗ trợ thành viên

- Khoá kiến trúc và API contract giữa RAG (Phúc) và UI ngay ở giờ đầu, để hai bên code song song không phải chờ nhau.
- Dựng giao diện chat, tích hợp với API backend.
- Hiển thị câu trả lời kèm trích dẫn nguồn và cảnh báo conflict rõ ràng trên UI.
- Check-in giữa các track tại các mốc chuyển giai đoạn (H10, H18, H26) để phát hiện sớm chỗ bị kẹt.
- Luyện "happy path" — chuỗi thao tác demo trực tiếp cho giám khảo, đảm bảo chạy mượt.
- Hỗ trợ các thành viên khác khi cần.

### Huy — Research dữ liệu pháp lý (thuvienphapluat.vn, phapdien.moj.gov.vn)

- Khai thác phapdien.moj.gov.vn để tìm chuỗi văn bản gốc + văn bản sửa đổi thật — hệ thống Pháp điển vốn đã tổ chức theo trạng thái còn hiệu lực/hết hiệu lực, rất hợp để lấy case amendment/partial supersession có thật thay vì phải tự bịa.
- Thu thập biểu lãi suất tiền gửi, quy định rút trước hạn, KYC, bảo hiểm tiền gửi.
- Ghi ngay ngày hiệu lực và trạng thái từng điều khoản ngay lúc thu thập, không để dồn việc gắn metadata cho Phúc.
- Chuẩn hóa định dạng file (có cấu trúc rõ theo điều/khoản) trước khi bàn giao cho Phúc.
- Tìm hoặc đánh dấu case mâu thuẫn giữa các quy định nếu có; nếu không đủ, phối hợp tạo case giả lập.

### Phúc — RAG core (tách nhỏ thành 10 việc)

| # | Việc | Mô tả | Ưu tiên |
|---|---|---|---|
| 1 | Chunking | Chia văn bản theo điều/khoản, không theo cấp file | Cao |
| 2 | Schema metadata | Định nghĩa trường ngày hiệu lực, trạng thái, văn bản liên quan | Cao |
| 3 | Embedding + vector DB | Chọn embedding model, nạp dữ liệu vào Chroma/FAISS | Cao |
| 4 | Retrieval cơ bản | Truy vấn trả về top-k chunk liên quan | Cao |
| 5 | Logic amendment | Lọc chọn văn bản có hiệu lực mới nhất | Cao |
| 6 | Logic partial supersession | Loại đúng phần điều khoản đã bị thay thế, giữ phần còn hiệu lực | Cao |
| 7 | Logic cross-reference | Mở rộng lấy thêm chunk liên quan qua bảng quan hệ văn bản | Cao |
| 8 | Logic conflict detection | So sánh nội dung các chunk còn hiệu lực, phát hiện mâu thuẫn | Cao |
| 9 | Prompt + generation | LLM tổng hợp câu trả lời tự nhiên, luôn kèm trích dẫn nguồn | Trung bình |
| 10 | API layer | Đóng gói thành endpoint để Dương gọi từ UI | Trung bình |

Việc 1-3 có thể bắt đầu ngay khi Huy có dữ liệu thô đầu tiên, không cần đợi đủ 100%. Việc 5-8 là phần ăn điểm nhất của đề bài, nên ưu tiên làm trước việc 9 (có thể chỉnh nhanh sau).

### Dũng — Research tài liệu tiền gửi các ngân hàng khác (Vietinbank...)

- Thu thập tài liệu sản phẩm tiền gửi của các ngân hàng khác để tham chiếu, đối sánh khi thiết kế case demo.

### Hòa — Tài liệu BA + slide pitching

- Viết mô tả giải pháp hoàn chỉnh cho form nộp bài.
- Soạn slide theo mạch: vấn đề → giải pháp → kiến trúc → demo.
- Lấy screenshot/kết quả thật từ demo của Dương và Phúc đưa vào slide, thay vì dùng mockup.
- Chuẩn bị sẵn câu trả lời cho các câu hỏi giám khảo hay hỏi (ví dụ: "nếu dữ liệu tăng lên hàng chục nghìn văn bản thì sao", "làm sao biết hệ thống không bịa thông tin").

### Phượng — Docker, CI/CD, deployment

- Viết Dockerfile/docker-compose đóng gói toàn bộ hệ thống, chạy ổn định trên máy khác.
- Viết script health-check đơn giản để cả team phát hiện ngay khi có phần bị lỗi.
- Đóng băng môi trường demo ít nhất 2 giờ trước khi trình bày, không update code phút chót.
- Chuẩn bị phương án chạy local nếu mất mạng lúc demo, không phụ thuộc hoàn toàn vào cloud.

## 4. Timeline chi tiết theo khối giờ

| Khung giờ | Công việc | Người phụ trách | Ưu tiên |
|---|---|---|---|
| H0–H2 | Kickoff: chốt phạm vi MVP, khoá kiến trúc/API contract, chia việc, setup môi trường | Cả team | Cao |
| H2–H10 | Thu thập & chuẩn hóa văn bản pháp lý (biểu lãi suất, quy định rút trước hạn, KYC, bảo hiểm tiền gửi) | Huy | Cao |
| H2–H10 | Thu thập tài liệu tiền gửi ngân hàng khác để đối sánh | Dũng | Trung bình |
| H2–H10 | Chunking + schema metadata + setup vector DB (RAG việc 1-3) | Phúc | Cao |
| H2–H10 | Dựng khung giao diện chat cơ bản (React/Next.js) | Dương | Trung bình |
| H2–H10 | Viết Dockerfile/docker-compose khung ban đầu | Phượng | Trung bình |
| H10–H18 | Retrieval cơ bản + logic amendment + partial supersession (RAG việc 4-6) | Phúc | Cao |
| H10–H18 | Soạn 15-20 câu hỏi test bao phủ cả 4 loại thách thức | Huy, Dũng | Cao |
| H10–H18 | Tích hợp UI với API RAG (bản đầu) | Dương | Cao |
| H18–H26 | Logic cross-reference + conflict detection (RAG việc 7-8) | Phúc | Cao |
| H18–H26 | Hiển thị trích dẫn nguồn + cảnh báo conflict trên UI | Dương | Cao |
| H18–H26 | Bắt đầu viết mô tả giải pháp + outline slide | Hòa | Trung bình |
| H26–H32 | Prompt engineering + hoàn thiện API layer (RAG việc 9-10) | Phúc | Cao |
| H26–H32 | Hoàn thiện UI, luyện happy path | Dương | Cao |
| H26–H32 | Đóng gói Docker hoàn chỉnh, viết health-check script | Phượng | Trung bình |
| H32–H38 | Test end-to-end với bộ câu hỏi, sửa lỗi phát sinh | Cả team | Cao |
| H38–H42 | Hoàn thiện slide, lấy screenshot/kết quả demo thật | Hòa | Trung bình |
| H42–H46 | Đóng băng môi trường demo, buffer sửa lỗi, trau chuốt | Phượng dẫn dắt, cả team | Thấp |
| H46–H48 | Rehearsal demo trực tiếp, rà soát checklist, nộp bài | Cả team | Cao |

## 5. Việc có thể cắt nếu thiếu thời gian

- Test hiệu năng/tải (load test) — không cần thiết cho demo hackathon.
- Quy định phụ (đồng sở hữu, thừa kế sổ tiết kiệm) — giữ lại nhóm cốt lõi: lãi suất, rút trước hạn, KYC, bảo hiểm tiền gửi.
- Video demo quay sẵn — thay bằng demo trực tiếp nếu ban tổ chức cho phép.
- Giao diện đẹp — ưu tiên chạy đúng hơn là polish UI/UX.
- CI/CD pipeline đầy đủ — chỉ cần Docker đóng gói chạy ổn định.

## 6. Checklist tối thiểu phải demo được

- 1 câu hỏi cross-reference: trả lời đúng bằng cách nối thông tin từ 2 văn bản liên quan.
- 1 câu hỏi amendment: trả lời đúng theo biểu lãi suất/quy định có hiệu lực mới nhất.
- 1 câu hỏi partial supersession: trả lời đúng phần điều khoản còn hiệu lực, loại đúng phần đã bị thay thế.
- 1 câu hỏi có tình huống conflict: hệ thống phát hiện và cảnh báo đúng mâu thuẫn.

## 7. Tech stack

Xem file riêng: `TechStack_RAG_TienGui_SHB.md`

## 8. Lưu ý

- Nên chia ca nghỉ luân phiên (tối thiểu 3-4 giờ/người) thay vì cả team thức xuyên 48 giờ, để tránh lỗi ở giai đoạn tích hợp cuối (H32-H38) — đây là giai đoạn dễ phát sinh bug nhất và cần đầu óc tỉnh táo.
- Ưu tiên tuyệt đối: có 4 câu trả lời demo đúng (mục 6) quan trọng hơn số lượng văn bản hay độ hoàn thiện giao diện.
- Huy nên bàn giao dữ liệu cho Phúc theo từng đợt nhỏ ngay khi có, không đợi gom đủ hết mới chuyển, để Phúc không bị chờ.
