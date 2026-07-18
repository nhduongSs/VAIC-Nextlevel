# data/discovery/ — Raw crawl output (chưa đúng format `data/raw/`)

Đây là kết quả **data discovery** (crawl thô, chưa chuẩn hoá) cho RAG Tiền gửi SHB, bàn giao
vào nhánh `data/deposit-corpus-discovery`. **Chưa nằm trong `data/raw/`** vì định dạng chưa
khớp với `document_loader.py` — cần chuyển đổi trước khi `python -m scripts.ingest` đọc được.
Đọc file này trước khi động vào bất kỳ file con nào.

## 0. Việc cần làm để đưa vào `data/raw/` (đọc trước tiên)

`document_loader.py` parse mỗi file `.md` bằng 2 regex cố định:

```
# <tiêu đề văn bản> | doc_id=<mã> | effective_date=YYYY-MM-DD | status=<trạng thái>
## Điều 1. <tên điều>
nội dung...
## Điều 2. <tên điều>
nội dung...
```

Dữ liệu trong `data/discovery/` **chưa ở format này** — đang là JSON thô từ API, HTML thô
trong PDF, hoặc markdown tóm tắt tự do. Việc chuyển đổi cần làm thủ công/bán tự động vì:

- **`base_docs/` (pháp lý)**: đã có sẵn nội dung điều/khoản thật trong text (field `markdown`
  hoặc `data.documentContent.content` tuỳ schema — xem mục 2) → **dễ chuyển đổi tự động**,
  chỉ cần viết script tách theo `Điều N.` đã có sẵn trong văn bản gốc.
- **`bank_docs/` (SHB + 4 ngân hàng so sánh)**: phần lớn là PDF bảng lãi suất/biểu phí,
  **không có cấu trúc Điều/Khoản** → phải tự quyết định cách "đóng khung" thành mục giả lập
  (ví dụ `## Điều 1. Lãi suất kỳ hạn 1 tháng`) hoặc bàn với người phụ trách backend
  (Phúc) xem có nên thêm 1 loader riêng cho dữ liệu sản phẩm ngân hàng (dạng bảng, không
  phải văn bản luật) thay vì ép vào khuôn Điều/Khoản.

### Mapping `status` — field bắt buộc, ảnh hưởng trực tiếp đến logic amendment (việc #5-6)

| Giá trị trong `eff_status`/`notes` của bộ data này | Map sang `status` field | Ý nghĩa cho RAG service |
|---|---|---|
| `Còn hiệu lực` | `hieu_luc` | Dùng bình thường |
| `Hết hiệu lực toàn bộ` | `het_hieu_luc` | `vector_store.py` đã lọc bỏ loại này (`status != 'het_hieu_luc'`) |
| `Hết hiệu lực một phần` | **chưa có giá trị chuẩn trong code** — cần Phúc quyết định (ví dụ `hieu_luc_mot_phan`) | Đây chính là case **"partial supersession" (việc #6, ăn điểm nhất theo brief)** |

### 🎯 2 case "partial supersession" CÓ THẬT, không cần giả lập (brief mục 3 có nhắc phải tự tạo case giả nếu không tìm được — đã tìm được rồi)

1. **Luật Các TCTD 32/2024/QH15** bị **Luật 96/2025/QH15** sửa đổi một phần (4 điều khoản cụ
   thể, xem `relations/luat/32_2024_QH15.json` field `relations.khac` và
   `relations/luat/96_2025_QH15.json`) — 32/2024 vẫn còn hiệu lực phần lớn, chỉ vài điều bị
   thay.
2. **Thông tư 04/2022/TT-NHNN** (lãi suất rút trước hạn) — `eff_status: "Hết hiệu lực một
   phần"`, xem `base_docs/thong_tu/04_2022_TT-NHNN.json`.

### 🎯 Case "amendment/supersession" đầy đủ chuỗi (việc #5)

**Luật Bảo hiểm tiền gửi**: 06/2012/QH13 (`Hết hiệu lực toàn bộ`) → bị thay hoàn toàn bởi
111/2025/QH15 (`Còn hiệu lực`) — xem `relations/luat/111_2025_QH15.json`, field
`relations.thay_the` ghi rõ quan hệ này. Chuỗi tương tự: Thông tư 24/2014/TT-NHNN
(`Hết hiệu lực toàn bộ`) → 04/2026/TT-NHNN (`Còn hiệu lực`).

### Mapping quan hệ văn bản → bảng `document_relations` (relation_store.py)

`graph_data.json` (gộp sẵn từ toàn bộ `relations/`) có field `rel` trên mỗi edge — map sang
`relation_type` mà `relation_store.py` cần:

| `rel` trong graph_data.json | `relation_type` cần cho Supabase |
|---|---|
| `thay_the` | `supersedes` |
| `sua_doi` | `amends` |
| `huong_dan`, `huong_dan_suy_luan` | `cross_reference` (hoặc bỏ qua nếu chỉ cần 3 loại chính) |
| `can_cu`, `khac` | `cross_reference` |

Field `superseded_clause` (điều khoản cụ thể bị thay) **chưa có sẵn** trong dữ liệu đã crawl —
quan hệ hiện ở cấp độ toàn văn bản, chưa tách đến từng Điều. Cần bổ sung thủ công cho 2 case
partial-supersession nêu trên nếu muốn demo đúng tính năng này.

## 1. Bắt đầu từ đâu (đọc file thô)

Đọc `catalog.json` trước — index phẳng, máy đọc được, liệt kê toàn bộ 50 tài liệu (16 văn bản
pháp lý + 34 tài liệu ngân hàng), mỗi dòng có sẵn: đường dẫn file, loại, độ tin cậy
(`confidence`), ghi chú gap nếu có.

Script sinh ra file này: `build_catalog.py` (không nằm trong repo này, ở máy người crawl —
xin lại nếu cần chạy lại sau khi crawl thêm).

## 2. Kiến trúc 2 lớp

```
data/discovery/
├── catalog.json              ← ĐỌC FILE NÀY TRƯỚC
├── graph_data.json           ← sơ đồ quan hệ giữa các văn bản pháp lý (đã map ở mục 0)
├── base_docs/    ┐
├── relations/     ┴─ LỚP 1: PHÁP LÝ (nền tảng chung, áp dụng mọi ngân hàng)
└── bank_docs/
    ├── shb/          ← LỚP 2a: NỘI BỘ SHB (ngân hàng chính, ưu tiên cao nhất)
    ├── bidv/       ┐
    ├── vietinbank/  │
    ├── vietcombank/ ┼─ LỚP 2b: SO SÁNH NGÂN HÀNG KHÁC (dữ liệu phụ, câu hỏi
    └── techcombank/ ┘   "so sánh lãi suất giữa các ngân hàng")
```

**Lớp 1 (Pháp lý)** trả lời câu hỏi mang tính quy định chung: hạn mức bảo hiểm tiền gửi, quy
tắc lãi suất rút trước hạn theo NHNN, điều kiện pháp lý của tiền gửi.

**Lớp 2a (SHB)** là nguồn trả lời chính cho phần lớn câu hỏi thực tế (lãi suất cụ thể, biểu
phí, thủ tục mở sổ tại SHB).

**Lớp 2b (4 ngân hàng khác)** chỉ phục vụ truy vấn so sánh — không cần chi tiết bằng lớp 2a.

## 3. Lớp Pháp lý — 2 schema khác nhau trong `base_docs/`

**Schema A** (4 file `thong_tu/48_*.json`): `{ doc_name, item_id, title, doc_number,
issue_date, markdown, structure_json, extracted_json, summary, ... }` → nội dung ở field
**`markdown`**.

**Schema B** (12 file còn lại): `{ success, data: { docNum, title, effFrom, effStatus,
documentContent: { content: "<html>..." }, references: [...] } }` → nội dung ở
**`data.documentContent.content`** (HTML thô, cần strip tag). `data.references[]` có sẵn quan
hệ văn bản qua `referenceType` (3=căn cứ, 9=hướng dẫn, 12=thay thế).

`catalog.json` đã chuẩn hoá `doc_number`/`title`/`eff_status` cho cả 2 schema.

## 4. Đề xuất mapping vào `data/raw/<loai>/` (4 thư mục brief gợi ý)

16 văn bản pháp lý không chia đều 4 thư mục gợi ý trong docstring `scripts/ingest.py`
(`lai_suat`, `rut_truoc_han`, `kyc`, `bao_hiem`) — đề xuất:

| Văn bản | Thư mục đề xuất |
|---|---|
| TT 48/2018, TT 49/2018, TT 07/2014→48/2024 (lãi suất) | `lai_suat/` |
| TT 04/2022/TT-NHNN (lãi suất rút trước hạn) | `rut_truoc_han/` |
| Luật 111/2025/QH15, Luật 06/2012/QH13, NĐ 68/2013, QĐ 32/2021 (bảo hiểm tiền gửi) | `bao_hiem/` |
| TT 04/2026/TT-NHNN (hướng dẫn bảo hiểm tiền gửi) | `bao_hiem/` |
| Luật 32/2024/QH15, 96/2025/QH15 (Các TCTD — nền tảng chung, không thuộc riêng 1 nhóm) | **cần thư mục thứ 5**, ví dụ `to_chuc_tin_dung/` — không ép vào 4 nhóm có sẵn |
| Pháp lệnh Ngoại hối 28/2005, NĐ 70/2014 (tiền gửi ngoại tệ) | `lai_suat/` hoặc thư mục `ngoai_hoi/` riêng nếu cần tách |
| TT 48/2014, 48/2025 (phát ngôn NHNN, thủ tục hành chính) | **không liên quan tiền gửi trực tiếp** — cân nhắc loại khỏi `data/raw/`, giữ trong discovery làm tham khảo |

Không có văn bản nào map vào `kyc/` — chưa crawl dữ liệu KYC (ngoài phần "giấy tờ xác minh
thông tin" nằm rải rác trong T&C của SHB, xem `bank_docs/shb/pdfs/quy_dinh_tien_gui_co_ky_han_khtc.pdf`).

## 5. Lớp Ngân hàng — chi tiết

### Cấu trúc mỗi ngân hàng (đồng nhất 5 ngân hàng)
```
bank_docs/<bank>/
├── manifest.json     ← index riêng (catalog.json đã gộp sẵn, ưu tiên dùng catalog)
├── pdfs/             ← PDF gốc chính thức từ website ngân hàng (độ tin cậy cao nhất)
└── pages/             ← JSON (API) hoặc Markdown (tóm tắt do AI viết lại)
```

### Category (field trong manifest.json/catalog.json)
| category | Ý nghĩa |
|---|---|
| `lai_suat_tien_gui` | Lãi suất tiền gửi — quan trọng nhất |
| `bieu_phi` | Biểu phí giao dịch tiền gửi |
| `dieu_khoan_san_pham` | T&C/quy định sản phẩm |
| `thu_tuc_mo_so` | Hồ sơ/thủ tục mở sổ |
| `lai_suat_co_so` | ⚠️ CHỈ ở SHB — lãi suất THAM CHIẾU CHO VAY, không phải lãi suất tiền gửi. Không dùng để trả lời câu hỏi lãi suất gửi tiền. |

### Độ tin cậy — field `confidence` trong catalog.json
| confidence | Ý nghĩa |
|---|---|
| `high` (PDF chính thức / API trực tiếp) | Coi là nguồn sự thật |
| `medium` (`markdown_summary`) | AI tóm tắt lại từ WebFetch/WebSearch, KHÔNG phải bản chụp nguyên văn — đối chiếu `source_url` trước khi dùng số liệu quan trọng |
| `gap` | Không lấy được — xem `notes` |

## 6. Gap đã biết (2 gap, đã xác định rõ nguyên nhân)

| Ngân hàng | Thiếu gì | Nguyên nhân | Đề xuất |
|---|---|---|---|
| **SHB** | Lãi suất tiền gửi VND cho **doanh nghiệp** | Xác nhận qua 2 văn bản T&C: SHB chỉ hiển thị lãi suất KHDN trong Internet Banking sau đăng nhập (`ibanking.shb.com.vn/corp`) hoặc tại quầy — không công bố công khai. Đặc điểm sản phẩm B2B thật, không phải lỗi crawl. | Câu hỏi lãi suất KHDN → trả lời hướng dẫn liên hệ chi nhánh, không bịa số |
| **Vietcombank** | 1 PDF biểu phí tiết kiệm riêng | File trên SharePoint (`portal.vietcombank.com.vn`), tên file Unicode tổ hợp gây lỗi tải | Dùng `bieu_phi_dich_vu_tai_khoan.pdf` (đã có) tạm thời |

VietinBank & Techcombank chưa có dữ liệu khách hàng doanh nghiệp (không phải gap chính thức,
chỉ chưa được yêu cầu ưu tiên khi crawl).

## 7. Cảnh báo kỹ thuật khi xử lý PDF

Nếu dùng `pdftotext` (poppler) đọc nhanh PDF, dấu tiếng Việt lỗi font (mojibake). File PDF gốc
vẫn nguyên vẹn Unicode. Khi viết script convert sang `data/raw/`, dùng `PyMuPDF`/`pdfplumber`
(test đọc đúng Unicode), tránh `pdftotext` CLI cho bước production.

## 8. Độ mới dữ liệu (tính đến 2026-07-18)

| Nguồn | Ngày hiệu lực dữ liệu |
|---|---|
| BIDV, Vietcombank (lãi suất) | Real-time API — đúng ngày crawl |
| VietinBank (lãi suất) | CMS cập nhật 2026-04-12 |
| Techcombank (lãi suất) | PDF hiệu lực 2026-03-28 |
| SHB (lãi suất cá nhân) | PDF hiệu lực 2026-04-11 |
| Văn bản pháp lý | Xem `eff_from`/`eff_status` từng văn bản trong `catalog.json` |

Không có cơ chế tự động refresh — đây là snapshot một lần.
