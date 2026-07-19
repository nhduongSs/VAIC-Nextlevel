"""
Định nghĩa các luật tĩnh (rule-based) dùng làm lớp chặn đầu tiên,
NHANH và RẺ hơn gọi LLM để phân loại. LLM chỉ dùng làm lớp thứ 2 (soft check).
"""

import re
import unicodedata

# --- Chủ đề được phép trả lời (giữ AI đúng phạm vi "tiền gửi") ---
IN_SCOPE_KEYWORDS = [
    "gửi tiền",
    "tiết kiệm",
    "lãi suất",
    "kỳ hạn",
    "sổ tiết kiệm",
    "tất toán",
    "đáo hạn",
    "tiền gửi",
    "mở sổ",
    "rút trước hạn",
    "bảo hiểm tiền gửi",
    "hạn mức bảo hiểm",
    "kyc",
    "định danh khách hàng",
    "gốc",
    "lãi nhập gốc",
    "chào",
    "cảm ơn",
    "xin chào",
    "hello",
    "hi",
]

# --- Yêu cầu KHÔNG được phép trả lời dù có vẻ liên quan ---
UNSAFE_PATTERNS = [
    r"rửa tiền",
    r"trốn thuế",
    r"giấu tiền",
    r"lách luật",
    r"gian lận lãi suất",
    r"làm giả (sổ|giấy tờ|chứng từ)",
    r"cách (hack|xâm nhập|bẻ khóa)",
    r"lãi suất (chắc chắn|cam kết) \d+%",
]

# --- Câu hỏi đòi tư vấn đầu tư / tài chính cá nhân vượt phạm vi ---
FINANCIAL_ADVICE_PATTERNS = [
    r"nên gửi (bao nhiêu|ngân hàng nào)",
    r"đầu tư (gì|vào đâu)",
    r"có nên (gửi|rút|đầu tư)",
    r"ngân hàng nào (tốt nhất|uy tín nhất|lãi cao nhất)",
]

# --- Câu chào hỏi / xã giao đơn giản — trả lời trực tiếp, KHÔNG chạy RAG,
# KHÔNG gắn trích dẫn nguồn tài liệu (tránh gắn nguồn pháp lý ngẫu nhiên vào
# câu "chào bạn"). Chỉ khớp toàn bộ tin nhắn (không phải substring) để không
# nuốt nhầm câu hỏi thật bắt đầu bằng "chào" (vd "chào bạn, lãi suất...").
# Patterns viết không dấu — input được bỏ dấu tiếng Việt trước khi so khớp
# (_strip_diacritics) để không phải liệt kê mọi biến thể dấu (á/à/ả/ã/ạ...).
SMALL_TALK_PATTERNS: dict[str, list[str]] = {
    "greeting": [
        r"(xin )?chao( (ban|shb|nextbank|admin))?",
        r"(hi|hello|hey|alo|halo)( (ban|there))?",
    ],
    "thanks": [
        r"cam ?on( ban)?( nhieu)?( nhe)?",
        r"thanks?( you)?",
    ],
    "farewell": [
        r"tam biet",
        r"bye( bye)?",
    ],
    "wellbeing": [
        r"ban (co )?khoe khong",
        r"how are you",
    ],
    "identity": [
        r"ban la ai",
        r"ban ten gi",
        r"ban co the (lam|giup) gi",
        r"who are you",
    ],
}


def _strip_diacritics(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "d")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def match_small_talk(text: str) -> str | None:
    """Return the small-talk category if the WHOLE message (after stripping
    diacritics/punctuation/whitespace) matches a known greeting/thanks/
    farewell/etc. pattern — or None if it doesn't (including "real"
    questions that merely start with a greeting word)."""
    normalized = _strip_diacritics(text.strip().lower())
    normalized = re.sub(r"[\s!?.,;]+", " ", normalized).strip()
    if not normalized:
        return None
    for category, patterns in SMALL_TALK_PATTERNS.items():
        for pattern in patterns:
            if re.fullmatch(pattern, normalized):
                return category
    return None


# --- PII cần lọc khỏi log / cảnh báo user không nên gửi ---
PII_PATTERNS = {
    "cccd_cmnd": r"\b\d{9}(\d{3})?\b",
    "so_tai_khoan": r"\b\d{8,16}\b",
    "so_dien_thoai": r"\b(0|\+84)\d{9,10}\b",
}

# --- Prompt injection cơ bản ---
INJECTION_PATTERNS = [
    r"bỏ qua (hướng dẫn|instruction|system prompt)",
    r"ignore (previous|the above) instructions?",
    r"bạn (bây giờ|từ giờ) là",
    r"you are now",
    r"act as (?!.*(nhân viên tư vấn))",
    r"jailbreak",
    r"DAN mode",
]


def matches_any(text: str, patterns: list[str]) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


def contains_pii(text: str) -> list[str]:
    found = []
    for label, pattern in PII_PATTERNS.items():
        if re.search(pattern, text):
            found.append(label)
    return found
