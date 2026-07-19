# User Requirements Document (URD) — SỔ VÀNG
## Trợ lý AI tư vấn & so sánh tiền gửi ngân hàng

| | |
|---|---|
| **Phiên bản** | 1.0 — 2026-07-19 |
| **Trạng thái** | Draft để review |
| **Tài liệu liên quan** | `v2_so-vang-tai-lieu-BA.docx` (BA), `doc/Software_Requirements_Specification_SRS.md` (SRS), `doc/Tai_lieu_BA_Nghiep_vu_Ngan_hang.md`, `doc/Kha_nang_mo_rong_Extensibility.md` |
| **Quy ước** | UR-xx = yêu cầu người dùng; trace sang FR-xx trong SRS. Giai đoạn: G1 (MVP) / G2 / G3 (B2B) / B2B+ |

---

## 1. Mục đích tài liệu

Mô tả **nhu cầu của người dùng bằng ngôn ngữ của người dùng** — điều họ cần đạt được, không
phải cách hệ thống hiện thực. Mỗi yêu cầu viết theo dạng user story kèm tiêu chí nghiệm thu
(acceptance criteria) để đội phát triển và người dùng cùng một cách hiểu. Chi tiết kỹ thuật
"hệ thống làm thế nào" nằm ở SRS.

## 2. Nhóm người dùng (User Classes)

| # | Nhóm | Đặc điểm | Giai đoạn |
|---|---|---|---|
| U1 | **Người gửi tiền cá nhân** | Không rành thuật ngữ pháp lý; cần nhanh, dễ hiểu, miễn phí; dùng điện thoại là chính | G1 |
| U2 | **Khách hàng doanh nghiệp / kế toán** | Quan tâm tiền gửi có kỳ hạn ngắn, điều kiện cho tổ chức, chứng từ | G1 (hỏi đáp), B2B+ (giao dịch ERP) |
| U3 | **Giao dịch viên (GDV) ngân hàng đối tác** | Cần tra cứu quy định trong lúc đang phục vụ khách — tốc độ và trích dẫn là sống còn | G3 |
| U4 | **Compliance / Legal ngân hàng đối tác** | Thẩm định câu trả lời; cần truy vết nguồn và cảnh báo mâu thuẫn | G3 |
| U5 | **Quản trị viên nội dung (đội SỔ VÀNG)** | Nạp văn bản, curate quan hệ, giám sát chất lượng | G1 |
| U6 | **RM (Relationship Manager) đối tác** | Nhận các câu hỏi vượt phạm vi bot kèm ngữ cảnh | B2B+ |

## 3. Yêu cầu người dùng

### 3.1 U1 — Người gửi tiền cá nhân

**UR-01 · Hỏi đáp quyền lợi bằng tiếng Việt tự nhiên** *(G1 — trace: FR-01)*
> Là người gửi tiền, tôi muốn hỏi bằng câu nói thường ngày ("500 triệu gửi 6 tháng rút sớm có
> mất lãi không?") và nhận câu trả lời dễ hiểu, để không phải tự đọc Thông tư.

Nghiệm thu: câu hỏi tự nhiên (không cần từ khóa chuẩn) được trả lời đúng nội dung văn bản còn
hiệu lực; câu trả lời có phần "nói đơn giản" trước, chi tiết pháp lý sau.

**UR-02 · Biết nguồn của câu trả lời** *(G1 — trace: FR-01, FR-08)*
> Tôi muốn thấy câu trả lời dựa trên điều luật nào hoặc số liệu cập nhật lúc nào, để tự kiểm
> chứng thay vì phải tin chatbot.

Nghiệm thu: mọi câu trả lời về quyền lợi có trích dẫn (số hiệu văn bản + Điều); mọi con số
lãi suất kèm ngân hàng nguồn + ngày hiệu lực.

**UR-03 · So sánh lãi suất nhiều ngân hàng trong một câu hỏi** *(G1 — trace: FR-02)*
> Tôi muốn hỏi "kỳ hạn 12 tháng ngân hàng nào lãi cao nhất?" và nhận bảng so sánh khách quan,
> để không phải mở từng website ngân hàng.

Nghiệm thu: bảng so sánh đủ các ngân hàng theo dõi, sắp theo lãi suất, ghi rõ ngày cập nhật;
thứ tự không bị ảnh hưởng bởi quan hệ thương mại.

**UR-04 · Hiểu bảo hiểm tiền gửi** *(G1 — trace: FR-01)*
> Tôi muốn biết tiền của tôi được bảo hiểm bao nhiêu và trong trường hợp nào, để yên tâm khi
> chọn nơi gửi.

Nghiệm thu: trả lời đúng hạn mức hiện hành (125.000.000đ theo QĐ 32/2021/QĐ-TTg) kèm nguồn;
giải thích được phạm vi áp dụng (loại tiền gửi, loại tổ chức).

**UR-05 · Được từ chối rõ ràng thay vì bị tư vấn ẩu** *(G1 — trace: FR-08, FR-11)*
> Khi tôi hỏi "nên gửi ngân hàng nào?" hoặc điều ngoài phạm vi, tôi muốn chatbot nói rõ nó
> không tư vấn đầu tư cá nhân và chỉ đưa dữ liệu khách quan, để tôi không bị dẫn dắt.

Nghiệm thu: câu hỏi tư vấn cá nhân hóa bị từ chối lịch sự kèm giải thích; không có câu trả
lời chứa cam kết ("chắc chắn", "đảm bảo sinh lời").

**UR-06 · Dùng miễn phí, không cần tài khoản, không bị khai thác dữ liệu** *(G1 — trace: NFR)*
> Tôi muốn hỏi ngay không cần đăng ký và không bị thu thập thông tin tài chính cá nhân, để
> dùng thử không rào cản.

Nghiệm thu: chat được ngay khi mở trang; không trường bắt buộc nhập thông tin cá nhân; chính
sách dữ liệu hiển thị công khai.

**UR-17 · Được gợi ý sản phẩm phù hợp với hoàn cảnh của tôi** *(B2B+ — trace: FR-17)*
> Khi tôi đã đăng nhập kênh của ngân hàng (vd SHB SAHA) và đồng ý chia sẻ dữ liệu, tôi muốn
> trợ lý biết số dư nhàn rỗi và sổ sắp đáo hạn của tôi để gợi ý đúng sản phẩm hiện có của
> ngân hàng (kèm lãi suất thật và điều kiện pháp lý), thay vì trả lời chung chung.

Nghiệm thu: chỉ kích hoạt khi đã đăng nhập + đồng ý rõ ràng (opt-in); gợi ý chỉ nằm trong
danh mục sản phẩm hiện có của ngân hàng, kèm lãi suất niêm yết + citation quy định (rút
trước hạn, BHTG); luôn có disclosure "dữ liệu khách quan, không phải khuyến nghị đầu tư";
có lối chuyển sang RM phụ trách. Background lấy từ: core Temenos (số dư, sổ đáo hạn), CRM
(phân khúc), SAHA (hành vi kênh), Product Catalog (danh mục + lãi suất) — qua Integration Hub.

### 3.2 U2 — Khách hàng doanh nghiệp / kế toán

**UR-07 · Phân biệt đúng quy định cho tổ chức** *(G1 — trace: FR-03)*
> Là kế toán doanh nghiệp, tôi muốn câu trả lời áp dụng đúng cho tổ chức (không lẫn quy định
> chỉ dành cho cá nhân như tiền gửi tiết kiệm TT 48/2018), để không làm sai thủ tục.

Nghiệm thu: câu hỏi có ngữ cảnh doanh nghiệp không bao giờ nhận trích dẫn từ văn bản chỉ áp
dụng cá nhân; câu trả lời ghi rõ đối tượng áp dụng.

**UR-08 · Đặt tiền gửi ngay trong ERP** *(B2B+ — trace: FR-15)*
> Tôi muốn tạo lệnh gửi tiền có kỳ hạn ngay trong phần mềm kế toán/ERP của công ty, được trợ
> lý tư vấn kỳ hạn và điều kiện rút trước hạn trước khi xác nhận, để không phải ra quầy.

Nghiệm thu: luồng ERP → tư vấn → duyệt nội bộ → phê duyệt ngân hàng → chứng từ điện tử trả
về ERP hoạt động end-to-end (BPMN mục 10.3 tài liệu BA).

### 3.3 U3 — Giao dịch viên ngân hàng đối tác

**UR-09 · Tra cứu quy định trong lúc phục vụ khách** *(G3 — trace: FR-06)*
> Là GDV, tôi muốn nhận câu trả lời kèm đúng Điều/Thông tư trong vài giây, để trả lời khách
> ngay tại quầy mà không phải gọi hỏi hội sở.

Nghiệm thu: thời gian phản hồi ≤ 5 giây; câu trả lời có trích dẫn Điều-level đủ để đọc lại
cho khách; thuật ngữ đúng nghiệp vụ.

**UR-10 · Luôn được cảnh báo khi quy định thay đổi** *(G2/G3 — trace: FR-07)*
> Tôi muốn hệ thống tự nói cho tôi biết khi văn bản tôi hay dùng đã bị thay thế hoặc có bản
> hợp nhất mới, để không tư vấn theo quy định cũ.

Nghiệm thu: câu trả lời dựa trên văn bản đã bị thay thế phải kèm cảnh báo và trỏ sang bản
mới; xem được timeline các phiên bản.

**UR-11 · Biết quy trình này ai phụ trách** *(B2B+ — trace: FR-14)*
> Tôi muốn hỏi "hồ sơ mở tài khoản tổ chức đang ở bước nào, ai phụ trách, SLA bao lâu" và
> nhận câu trả lời từ hệ thống quy trình nội bộ, để hướng dẫn khách chính xác.

Nghiệm thu: câu hỏi quy trình trả về đúng process owner/SLA từ BPM của ngân hàng (qua
Integration Hub), không phải câu trả lời chung chung.

### 3.4 U4 — Compliance / Legal đối tác

**UR-12 · Truy vết được mọi câu trả lời** *(G3 — trace: FR-01, NFR kiểm toán)*
> Là compliance officer, tôi muốn truy ngược từ bất kỳ câu trả lời nào về đúng đoạn văn bản
> nguồn hoặc bản ghi lãi suất, để thẩm định và lưu hồ sơ kiểm toán.

Nghiệm thu: mỗi câu trả lời truy vết được citation (văn bản, Điều, ngày hiệu lực) hoặc bản
ghi Rate DB (ngân hàng, kỳ hạn, ngày); log đầy đủ theo phiên.

**UR-13 · Nhìn thấy mâu thuẫn giữa các văn bản** *(G2/G3 — trace: FR-09)*
> Tôi muốn được cảnh báo khi hai quy định còn hiệu lực vênh nhau về cùng một vấn đề, kèm cả
> hai nguồn, để đánh giá rủi ro thay vì vô tình chỉ thấy một phía.

Nghiệm thu: khi ngữ cảnh chạm cặp văn bản mâu thuẫn đã curate, câu trả lời hiển thị cảnh báo
+ trích dẫn cả hai phía + mô tả điểm vênh.

### 3.5 U5 — Quản trị viên nội dung

**UR-14 · Cập nhật tri thức không cần lập trình viên** *(G1 — trace: FR-12)*
> Là người quản trị nội dung, tôi muốn đưa văn bản mới vào hệ thống bằng quy trình nạp liệu
> chuẩn (không sửa code, không chờ release), để chatbot phản ánh quy định mới trong ngày.

Nghiệm thu: thêm file văn bản + chạy ingest → chatbot trả lời theo văn bản mới; bản cũ tự bị
đánh dấu thay thế nếu đã khai báo quan hệ.

**UR-15 · Giám sát chất lượng trả lời** *(G2 — trace: FR-13)*
> Tôi muốn xem hệ thống đang trả lời từ nguồn nào, tỷ lệ từ chối, các cảnh báo conflict đã
> bật, để phát hiện suy giảm chất lượng sớm.

Nghiệm thu: log có cấu trúc theo từng bước pipeline; thống kê citation/conflict/từ chối truy
xuất được theo ngày.

### 3.6 U6 — RM đối tác

**UR-16 · Nhận handoff kèm ngữ cảnh** *(B2B+ — trace: FR-14)*
> Là RM, khi khách hỏi vượt phạm vi chatbot, tôi muốn nhận yêu cầu kèm nguyên văn hội thoại
> và thông tin phân khúc, để tiếp nối mà không bắt khách kể lại từ đầu.

Nghiệm thu: yêu cầu handoff xuất hiện trên RM Workbench với transcript + lý do chuyển.

## 4. Kỳ vọng phi chức năng (góc nhìn người dùng)

| Kỳ vọng | Người dùng cảm nhận |
|---|---|
| Nhanh | Trả lời ≤ 5 giây; không "đang gõ" quá lâu |
| Đúng | Con số khớp 100% nguồn; không bao giờ "bịa" điều luật |
| Trung thực | Không biết thì nói không biết; trung lập giữa các ngân hàng |
| Sẵn sàng | Dùng được 24/7, có thông báo tử tế khi bảo trì |
| Riêng tư | Không bị hỏi/lưu thông tin tài chính cá nhân khi chưa đồng ý |
| Tiếng Việt chuẩn | Hiểu từ nghiệp vụ lẫn cách nói đời thường ("rút sớm", "đáo hạn") |

## 5. Ràng buộc & giả định

- Sản phẩm **không thực hiện giao dịch thật** ở G1–G3 (chỉ tư vấn/tra cứu); giao dịch ERP là
  giai đoạn B2B+ và luôn qua phê duyệt của ngân hàng đối tác.
- Sản phẩm **không đưa khuyến nghị đầu tư cá nhân hóa** — ràng buộc pháp lý, đồng thời là
  cam kết định vị trung lập.
- Dữ liệu lãi suất G1 lấy từ nguồn công khai chính thức của ngân hàng; độ tươi phụ thuộc
  lịch cập nhật (FR-04) cho tới khi có tích hợp trực tiếp với đối tác (B2B).
- Người dùng B2C không cần tài khoản; người dùng B2B đăng nhập theo phân quyền đối tác.

## 6. Ma trận truy vết URD → SRS

| UR | FR liên quan | Giai đoạn |
|---|---|---|
| UR-01, UR-02, UR-04 | FR-01, FR-08 | G1 |
| UR-03 | FR-02, FR-04, FR-05 | G1–G2 |
| UR-05 | FR-08, FR-11 | G1 |
| UR-06 | NFR bảo mật/riêng tư | G1 |
| UR-07 | FR-03 | G1 |
| UR-08 | FR-15 | B2B+ |
| UR-09 | FR-06 | G3 |
| UR-10 | FR-07, FR-10 | G2–G3 |
| UR-11, UR-16 | FR-14 | B2B+ |
| UR-12 | FR-01 + NFR kiểm toán | G3 |
| UR-13 | FR-09 | G2–G3 |
| UR-14 | FR-12 | G1 |
| UR-15 | FR-13 | G2 |
| UR-17 | FR-17 (+FR-14 Hub) | B2B+ |
