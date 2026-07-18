# Sản phẩm tiền gửi tiết kiệm có kỳ hạn — Techcombank
Nguồn: https://techcombank.com/en/personal/save/term-deposit (crawl 2026-07-18, qua WebFetch)

## Các loại sản phẩm
1. **Tiết kiệm thường** — cho rút trước hạn, hưởng lãi suất không kỳ hạn cho phần rút trước.
2. **Tiết kiệm Phát Lộc** — lãi suất cao hơn nhưng **không cho rút trước hạn**.
3. **Tiết kiệm trả lãi trước** — trả lãi ngay khi gửi.

## Số tiền gửi tối thiểu
| Sản phẩm | VND | Ngoại tệ |
|---|---|---|
| Thường / Phát Lộc | 1,000,000 | 100 đơn vị |
| Trả lãi trước | 5,000,000 | 500 đơn vị |

## Kỳ hạn
1-3 tuần, 1-36 tháng.

## Loại tiền
- VND: cả 3 sản phẩm.
- Ngoại tệ (USD, EUR, AUD, GBP, JPY, SGD): Tiết kiệm thường & Trả lãi trước.
- USD, EUR: Tiết kiệm Phát Lộc.

## Rút trước hạn
- Tiết kiệm thường & Trả lãi trước: được phép, hưởng lãi suất không kỳ hạn.
- **Tiết kiệm Phát Lộc: không được rút trước hạn** (khác biệt quan trọng so với BIDV/VietinBank/Vietcombank/Agribank).

## Đối tượng & kênh
- Giao dịch online: công dân VN cư trú/không cư trú và người nước ngoài cư trú hợp pháp tại VN ≥ 6 tháng.
- Kênh: chi nhánh, app Techcombank Mobile, Internet Banking.

## Phân khúc khách hàng (ảnh hưởng lãi suất — xem PDF `bieu_lai_suat_tien_gui_tiet_kiem_2026-03-28.pdf`)
Techcombank phân biệt lãi suất theo **hạng khách hàng** (Private, Priority, Inspire, Khách
hàng thường) và **số dư** (dưới 1 tỷ / 1-3 tỷ / trên 3 tỷ) — khác hẳn 4 ngân hàng quốc doanh
(chỉ có 1 mức lãi suất chung theo kỳ hạn). Đây là điểm khác biệt quan trọng cần chatbot RAG
xử lý đúng khi so sánh.
