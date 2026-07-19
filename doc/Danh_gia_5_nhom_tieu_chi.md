# Đánh giá SHB RAG Chatbot theo 5 nhóm tiêu chí — đối chiếu với chatbot 4 ngân hàng

> Tài liệu đánh giá theo framework 5 nhóm tiêu chí, đọc kèm `So_sanh_chatbot_5_ngan_hang.md`
> (bảng tổng hợp), `So_sanh_tieu_chi_Knowledge_Intelligence.md` (4 tính năng KI) và
> `Giai_thich_co_che_Ontology.md` (cơ chế ontology).
> Mọi nhận định về hệ thống của bạn đều grounded trên code thật trong repo; nhận định về
> 4 ngân hàng (BIDV, VietinBank, Vietcombank, Techcombank) dựa trên công bố công khai.

Cập nhật: 2026-07-19.

---

## 1. Mức độ hoàn thiện trải nghiệm khách hàng (CX)

### Hệ thống của bạn có gì (theo `frontend/components/`)

- **Trả lời có cấu trúc, không chỉ text**: `RateTableCard` render bảng lãi suất so sánh trực
  quan; `InterestCalculatorCard` tính lãi ngay trong chat; `QuickReplies` gợi ý câu hỏi tiếp
  theo — user không phải tự nghĩ cách hỏi.
- **Minh bạch nguồn ngay trên UI**: `SourcePill` gắn citation (số hiệu văn bản, Điều) vào từng
  câu trả lời — user click để verify; `ConflictNotice` cảnh báo trực quan khi 2 văn bản vênh
  nhau, hiển thị cả 2 phía.
- **Trải nghiệm hội thoại chuẩn**: `TypingIndicator`, `MessageList`/`MessageBubble`,
  session-based chat (`session_id` trong API), sidebar điều hướng, màn hình login + admin
  riêng (Next.js 14, đã vá CVE-2025-55184/67779).
- **Từ chối có kiểm soát thay vì trải nghiệm cụt**: khi ngoài phạm vi (retrieval guard, input
  guard) — bot nói rõ lý do từ chối thay vì trả lời sai hoặc im lặng.

### Đối chiếu 4 ngân hàng

Bot của họ mạnh ở **độ phủ kênh** (app, website, Facebook Messenger; VietinBank thêm VoiceBot
từ 02/2026) và tính ổn định của kịch bản. Nhưng trải nghiệm là **menu/intent tĩnh**: câu ngoài
kịch bản → "vui lòng liên hệ tổng đài"; không citation, không cảnh báo, không công cụ tính
toán trong hội thoại.

| Khía cạnh CX | Bạn | 4 ngân hàng |
|---|---|---|
| Structured response (bảng, calculator, quick replies) | ✅ | ❌ text/menu tĩnh |
| Citation hiển thị trên UI | ✅ SourcePill | ❌ |
| Cảnh báo mâu thuẫn trực quan | ✅ ConflictNotice | ❌ |
| Câu hỏi tự do ngoài kịch bản | ✅ nếu corpus có | ❌ chuyển tổng đài |
| Độ phủ kênh (app/social/voice) | ❌ mới 1 web UI | ✅ đa kênh, VoiceBot |

**Gap thật cần nói khi pitch**: chưa đa kênh, chưa có voice, chưa đo CSAT thực tế — đây là bài
toán vận hành, không phải giới hạn kiến trúc.

---

## 2. Chất lượng thông tin & Độ chính xác

### Hệ thống của bạn có gì

Đây là nhóm tiêu chí bạn **vượt trội nhất về cấu trúc** — toàn bộ tầng Knowledge Intelligence
phục vụ nó:

- **Grounding bắt buộc**: LLM chỉ trả lời từ context đã retrieve; retrieval guard từ chối khi
  context không đủ liên quan → chặn hallucination ở tầng kiến trúc, không phụ thuộc "LLM ngoan".
- **Đúng hiệu lực**: version resolution (REPLACES → score penalty + version note), filter
  `exclude_expired` ngay tầng SQL, Timeline Builder cho lịch sử văn bản.
- **Đúng độ phân giải**: chunking theo Điều (474 Điều nguyên vẹn), partial supersession loại
  đúng điều khoản đã bị thay, giữ phần còn hiệu lực.
- **Đúng thẩm quyền**: Authority Ranking (Luật 1.0 > Thông tư 0.8 > ... > FAQ 0.1).
- **Đúng con số**: câu hỏi số liệu route sang SQL trên `bank_products` (dữ liệu crawl từ nguồn
  chính thức 5 ngân hàng, có `effective_date`) — không để LLM tự so sánh số từ text.
- **Truy vết được**: mọi câu trả lời kèm citation Điều-level; mâu thuẫn được phơi ra kèm cả 2
  nguồn thay vì chọn ngầm 1 phía.
- **Target đo lường đã định nghĩa**: Retrieval Precision@5 ≥ 85%, Answer Faithfulness ≥ 90%,
  Conflict Detection accuracy ≥ 80% (architecture doc 00).

### Đối chiếu 4 ngân hàng

FAQ tĩnh **chính xác tại thời điểm soạn** — nhưng độ chính xác phụ thuộc con người nhớ cập
nhật kịch bản khi NHNN đổi quy định; không citation nên user không verify được; không có khái
niệm hiệu lực văn bản. Điểm cộng của họ: không hallucinate (vì không generate).

| Khía cạnh | Bạn | 4 ngân hàng |
|---|---|---|
| Chống hallucination | ✅ retrieval guard + grounding | ✅ (bằng cách không generate) |
| Tự động đúng hiệu lực khi quy định đổi | ✅ version resolution | ❌ cập nhật tay |
| Citation verify được | ✅ Điều-level | ❌ |
| Độ chính xác số liệu | ✅ SQL + effective_date | ⚠️ đúng nếu kịch bản mới |
| Phát hiện & cảnh báo mâu thuẫn | ✅ | ❌ |

---

## 3. Năng lực xử lý tác vụ & Ra quyết định

### Hệ thống của bạn có gì

- **Intent routing** (`rag_service.py`): tự nhận diện tên ngân hàng, cá nhân/doanh nghiệp từ
  query → filter metadata; câu so sánh số liệu → route sang SQL path thay vì semantic path.
- **Tác vụ so sánh liên ngân hàng**: `/rates/compare` trả bảng so sánh 5 ngân hàng theo
  `term_months` — tác vụ mà bot của chính các ngân hàng về cấu trúc không bao giờ làm.
- **Tác vụ tính toán**: InterestCalculatorCard — từ tra cứu sang hành động ngay trong chat.
- **Ra quyết định trong pipeline**: KI pipeline là chuỗi quyết định tự động — chọn bản còn
  hiệu lực, loại điều khoản chết, ưu tiên nguồn thẩm quyền cao, quyết định có cảnh báo conflict
  hay không (chunk-scoped, logic OR có chủ đích), quyết định từ chối khi context yếu.
- **Biết giới hạn của mình**: câu tư vấn tài chính cá nhân ("nên gửi hay mua vàng?") → guard
  chặn — không ra quyết định thay user ở vùng compliance cấm.

### Đối chiếu 4 ngân hàng

Bot của họ xử lý tốt **tác vụ giao dịch đóng gói** (khóa thẻ, tra số dư, đăng ký dịch vụ —
tích hợp core banking, eKYC) — đây là thứ bạn chưa có. Nhưng khả năng "ra quyết định" của
chúng dừng ở chọn intent; không suy luận trên tri thức, không tổng hợp đa nguồn.

| Khía cạnh | Bạn | 4 ngân hàng |
|---|---|---|
| Suy luận đa văn bản (multi-doc synthesis) | ✅ graph expansion | ❌ |
| So sánh liên ngân hàng | ✅ | ❌ (cấu trúc không cho phép) |
| Tác vụ giao dịch (khóa thẻ, chuyển tiền...) | ❌ ngoài scope | ✅ tích hợp core banking |
| Từ chối đúng lúc (biết giới hạn) | ✅ guard 3 tầng | ⚠️ fallback tổng đài |

**Định vị khi pitch**: bạn không cạnh tranh ở tác vụ giao dịch — bạn là **knowledge & decision
support layer** (cho nhân viên + khách hàng), bổ sung chứ không thay thế transactional bot.

---

## 4. Bảo mật, An toàn & Quản trị rủi ro

### Hệ thống của bạn có gì

- **Guardrails 3 tầng như một pipeline** (`app/guardrails/rules.py`, `guardrail_service.py`,
  có `test_guardrails.py` riêng):
  - *Input guard*: chặn prompt injection, unsafe request, PII, whitelist chủ đề, chặn câu tư
    vấn tài chính cá nhân (compliance NHNN về tư vấn đầu tư).
  - *Retrieval guard*: không đủ context → từ chối, chặn hallucination — rủi ro lớn nhất của
    LLM trong banking.
  - *Output guard*: lọc cụm từ cam kết rủi ro ("chắc chắn lãi", "đảm bảo sinh lời"...) trước
    khi trả về user.
- **Quản trị rủi ro thông tin**: conflict detection + authority ranking chính là risk
  management cho tri thức — user (và compliance officer) thấy được điểm vênh giữa các văn bản
  thay vì vô tình đứng trên điều khoản tranh chấp.
- **Hạ tầng**: JWT auth (`JWT_SECRET_KEY`), login + admin tách vai trò, secrets qua env
  (không hardcode), Next.js đã vá CVE-2025-55184/67779, structured logging (structlog) ghi
  lại pipeline từng bước — có audit trail cho mọi câu trả lời.
- **Kiến trúc giảm attack surface**: một PostgreSQL duy nhất, không multi-DB sync; LLM chỉ
  nhận context đã qua guard, không truy cập trực tiếp dữ liệu.

### Đối chiếu 4 ngân hàng

Ngân hàng lớn có ưu thế tuyệt đối về **hạ tầng an ninh tổ chức** (SOC, chứng chỉ ISO 27001/
PCI DSS, đội ngũ security riêng, eKYC + biometrics). Nhưng ở tầng **AI safety** thì mô hình
của họ đơn giản là *không cho AI tự do* — an toàn bằng cách bó năng lực. Bạn chứng minh được
mệnh đề khó hơn: **generative AI + guardrails vẫn kiểm soát được trong banking**.

| Khía cạnh | Bạn | 4 ngân hàng |
|---|---|---|
| AI-specific guardrails (injection, output filter) | ✅ 3 tầng, có test | N/A (không có LLM để bảo vệ) |
| Chống cam kết rủi ro / tư vấn sai compliance | ✅ output guard + input guard | ✅ (kịch bản được duyệt sẵn) |
| Audit trail cho từng câu trả lời | ✅ structured logging + citation | ⚠️ log hội thoại thường |
| An ninh hạ tầng tổ chức (SOC, ISO, PCI) | ❌ hackathon stage | ✅ |

---

## 5. Khả năng vận hành & Cải tiến liên tục

### Hệ thống của bạn có gì

- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`), quality gates Ruff + MyPy + Pytest;
  deploy Docker Compose lên GCP VM (`docker-compose.gcp.yml`) + Railway cho frontend.
- **Test suite thật**: 9 file test — KI pipeline (~740 dòng), guardrails, chat service,
  DeepSeek client, prompt builder, response formatter, document relations — vùng rủi ro cao
  nhất (KI + guard) được cover dày nhất.
- **Cập nhật tri thức không cần release**: quy định mới → thêm file vào `data/raw/` + chạy
  `scripts/ingest.py` → chatbot trả lời theo văn bản mới, version resolution tự xử lý bản cũ.
  So với chatbot kịch bản: mỗi thay đổi quy định là một đợt viết lại intent tay.
- **Cấu hình runtime**: toàn bộ KI pipeline bật/tắt/tinh chỉnh qua settings
  (`KI_CONFLICT_DETECTION_ENABLED`, `KI_EXPANSION_DEPTH`, `KI_AUTHORITY_WEIGHT`,
  hybrid alpha/beta...) — tune không cần sửa code.
- **Observability**: structlog đo latency từng processor (`processor_executed`,
  `pipeline_complete`), statistics trong mỗi ContextPackage (chunk count, conflict count,
  expansion count) — biết chính xác pipeline làm gì với từng câu hỏi.
- **Kiến trúc mở cho cải tiến**: Repository pattern → thay pgvector bằng Qdrant không đụng
  service layer; metrics target đã định nghĩa sẵn (Precision@5, Faithfulness) làm baseline
  cho evaluation loop; roadmap có sẵn trong architecture docs (crawler NHNN tự động,
  fine-tune, RBAC-aware retrieval).
- **Khả năng mở rộng vào hệ sinh thái SHB** (chi tiết + BPMN: `Kha_nang_mo_rong_Extensibility.md`):
  SHB đã chạy trên nền tảng **Temenos với kiến trúc mở (open APIs, microservices, Micro
  Apps)** — hệ thống này thiết kế sẵn các điểm cắm khớp vào đó:
  - *Central Integration Hub*: thay đường truy vấn thẳng vào DB Lớp C bằng Hub → Fee & Rate
    Management (số liệu real-time), CRM (cá nhân hóa), RM Workbench (handoff kèm hội thoại),
    BPM (trả lời "quy trình này ai phụ trách, SLA bao lâu") — chatbot chỉ biết 1 contract,
    đổi hệ thống đích không cần deploy lại.
  - *Kênh*: nhúng SHB SAHA (bán lẻ), SHB Corporate (doanh nghiệp), VoiceBot — backend giữ
    nguyên, chỉ thêm channel adapter.
  - *Giao dịch*: flow doanh nghiệp đặt tiền gửi từ ERP (advisory của chatbot tái dùng 100%,
    orchestration qua BPM + core banking).
  - *Domain mới*: tín dụng, thanh toán quốc tế... — áp lại ontology template, công sức chủ
    yếu là corpus, không phải code.

### Đối chiếu 4 ngân hàng

Họ mạnh về **vận hành quy mô lớn** (SLA, monitoring 24/7, đội vận hành riêng — BIDV 65k
interactions/ngày). Nhưng chu trình cải tiến của intent-bot là **thủ công tuyến tính**: thêm
tri thức = thêm kịch bản tay; nền tảng thuê ngoài (FPT.AI) nghĩa là cải tiến lõi phụ thuộc
vendor.

| Khía cạnh | Bạn | 4 ngân hàng |
|---|---|---|
| Cập nhật tri thức mới | ✅ ingest lại, tự động resolve version | ❌ viết kịch bản tay |
| CI/CD + quality gates | ✅ Ruff/MyPy/Pytest/Actions | ✅ (quy trình doanh nghiệp) |
| Observability tầng AI (per-processor latency, statistics) | ✅ | ⚠️ phụ thuộc vendor |
| Làm chủ công nghệ lõi | ✅ tự build toàn bộ | ⚠️ VCB thuê FPT.AI |
| Vận hành quy mô lớn, SLA 24/7 | ❌ chưa | ✅ |

---

## Bảng tổng kết 5 nhóm tiêu chí

| # | Nhóm tiêu chí | Bạn thắng ở | Họ thắng ở | Kết luận |
|---|---|---|---|---|
| 1 | CX | Structured response, citation UI, conflict notice, câu hỏi tự do | Đa kênh, voice, độ phủ | Chất lượng từng câu trả lời vs độ rộng kênh |
| 2 | Chất lượng & chính xác | Toàn bộ tầng KI: version, supersession, authority, SQL số liệu, citation | Không hallucinate (vì không generate) | **Thắng tuyệt đối về cấu trúc** |
| 3 | Tác vụ & quyết định | Suy luận đa văn bản, so sánh liên ngân hàng, biết giới hạn | Tác vụ giao dịch core banking | Định vị bổ sung, không thay thế |
| 4 | Bảo mật & rủi ro | AI guardrails 3 tầng, audit trail, quản trị rủi ro tri thức | Hạ tầng an ninh tổ chức | Bạn giải bài AI safety — bài họ chưa chạm tới |
| 5 | Vận hành & cải tiến | Ingest-to-answer tự động, observability AI, làm chủ lõi, **điểm cắm sẵn vào Temenos open APIs (Hub → CRM/BPM/Fee Mgmt)** | Quy mô, SLA, đội vận hành | Tốc độ tiến hóa + khả năng mở rộng vs quy mô hiện tại |

**Thông điệp xuyên suốt**: 4 ngân hàng tối ưu một chatbot **giao tiếp** ở quy mô lớn; bạn xây
một hệ thống **tri thức có kiểm soát** — nơi mỗi câu trả lời đúng hiệu lực, đúng thẩm quyền,
truy vết được, và tự cập nhật khi pháp luật thay đổi. Hai bài toán khác nhau; bài của bạn là
bài chưa ai trong 4 ngân hàng giải.
