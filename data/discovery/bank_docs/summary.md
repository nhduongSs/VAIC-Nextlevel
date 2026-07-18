# Tóm tắt crawl dữ liệu tiền gửi — BIDV, VietinBank, Vietcombank, Techcombank
Crawl ngày: 2026-07-18 (cập nhật lần 3 — thay Agribank bằng Techcombank theo yêu cầu)

## Bảng lãi suất tiền gửi cá nhân — VND, kỳ hạn phổ biến (khách hàng thường, gửi tại quầy)

| Kỳ hạn | BIDV | VietinBank | Vietcombank | Techcombank (KH thường, Phát Lộc tại quầy) |
|---|---|---|---|---|
| Không kỳ hạn | 0.1% | 0.1% | 0.1% | 0.05% (Phát Lộc Online) |
| 1 tháng | 2.1% | 2.1% | 2.1% | 4.15% |
| 3 tháng | 2.4% | 2.4% | 2.4% | 4.45% |
| 6 tháng | 3.5% | 3.5% | 3.5% | 6.65% |
| 12 tháng | 5.9% | 5.9% | 5.9% | 6.85% |
| 24 tháng | 6.0% | 6.0% | 6.0% | 5.85% |

**3 ngân hàng quốc doanh (BIDV/VietinBank/Vietcombank) khớp tuyệt đối** theo từng kỳ hạn —
đặc điểm thật của nhóm Big 4 đồng bộ lãi suất huy động. **Techcombank (tư nhân) cao hơn đáng
kể ở các kỳ hạn ngắn/trung** (6-12 tháng chênh 1-3 điểm %) nhưng **thấp hơn ở kỳ hạn dài 24
tháng** — đúng theo cấu trúc lãi suất một ngân hàng thương mại cổ phần cạnh tranh huy động
vốn ngắn/trung hạn.

⚠️ Bảng trên chỉ là 1 lát cắt (khách hàng thường, số dư bất kỳ). **Techcombank còn phân biệt
lãi suất theo hạng khách hàng (Private/Priority/Inspire/Thường) và số dư (<1 tỷ/1-3 tỷ/>3 tỷ),
cũng như theo kênh (tại quầy/online) và loại sản phẩm (Phát Lộc/Rút gốc linh hoạt)** — RAG
cần đọc đầy đủ PDF `techcombank/pdfs/bieu_lai_suat_tien_gui_tiet_kiem_2026-03-28.pdf` (3
trang, nhiều bảng) chứ không chỉ dùng bảng rút gọn này.

## Trạng thái dữ liệu theo ngân hàng

| Ngân hàng | Lãi suất | Biểu phí | T&C sản phẩm | Thủ tục mở sổ |
|---|---|---|---|---|
| **BIDV** | ✅ API trực tiếp (cá nhân) | ✅ PDF (cá nhân + doanh nghiệp) | ✅ PDF (108 trang) | ✅ tóm tắt từ blog |
| **VietinBank** | ✅ trích từ RSC payload (cá nhân, 20 kỳ hạn) | ⚠️ chỉ có phí TK thanh toán | ✅ PDF | ✅ tóm tắt từ trang sản phẩm |
| **Vietcombank** | ✅ API trực tiếp (cá nhân + doanh nghiệp) | ✅ PDF (tài khoản chung) | ❌ trang SPA, chỉ có tóm tắt gián tiếp | ⚠️ tóm tắt gián tiếp, độ tin cậy thấp hơn |
| **Techcombank** | ✅ PDF chính thức (28/03/2026), rất chi tiết — 4 sản phẩm × hạng KH × số dư | ✅ PDF chung + PDF riêng cho tiết kiệm | ✅ PDF T&C Phát Lộc Online (10 trang) | ✅ tóm tắt từ trang sản phẩm |

**4/4 ngân hàng hiện đều có dữ liệu lãi suất đã xác thực từ nguồn chính thức** (không còn GAP nào).

## Kỹ thuật đã dùng để lấy lãi suất không qua browser automation (bị chặn cho domain ngân hàng)

1. **BIDV**: endpoint AJAX lộ trực tiếp trong HTML tĩnh (`url: "/ServicesBIDV/InterestDetailServlet"`), gọi thẳng bằng POST rỗng.
2. **VietinBank**: trang Next.js App Router dùng RSC streaming (`self.__next_f.push(...)`) — toàn bộ dữ liệu server-render (kể cả bảng lãi suất từ CMS Directus) nằm ngay trong HTML tĩnh dưới dạng chuỗi JSON escape, chỉ cần parse đúng cách thay vì tìm bảng HTML thường.
3. **Vietcombank**: endpoint thật (`en/api/interestrates?accountType=Personal|Corporate`) không có trong HTML mà nằm trong thuộc tính `data-properties` của một DOM element (JSON encode sẵn), được đọc bởi đoạn JS trong bundle theme — phải tải và đọc bundle JS để tìm ra cách trang tự construct URL, sau đó gọi lại y hệt.
4. **Techcombank**: trang chính (Adobe Experience Manager) không nhúng dữ liệu tĩnh, không dùng RSC/data-properties — không dò được cơ chế client-fetch. Chuyển hướng: tìm trực tiếp PDF biểu lãi suất chính thức trên domain techcombank.com qua tìm kiếm — có sẵn, cập nhật thường xuyên, dùng `pdftotext -layout` để đọc lại khi cần.

## Ghi chú lịch sử: Agribank (đã loại khỏi bộ 4 theo yêu cầu người dùng)

Trước đó có crawl Agribank (biểu phí, T&C, thủ tục — đầy đủ) nhưng **không lấy được lãi suất**
vì đây là ngân hàng duy nhất có WAF chặn bot thực sự (F5 BIG-IP, chặn cả tải JS tĩnh). Đã xoá
thư mục `output/bank_docs/agribank/` theo yêu cầu "thay agribank bằng techcombank".
