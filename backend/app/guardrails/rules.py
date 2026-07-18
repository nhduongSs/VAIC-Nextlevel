"""
Định nghĩa các luật tĩnh (rule-based) dùng làm lớp chặn đầu tiên,
NHANH và RẺ hơn gọi LLM để phân loại. LLM chỉ dùng làm lớp thứ 2 (soft check).
"""
import re

# --- Chủ đề được phép trả lời (giữ AI đúng phạm vi "tiền gửi") ---
IN_SCOPE_KEYWORDS = [
    "gửi tiền", "tiết kiệm", "lãi suất", "kỳ hạn", "sổ tiết kiệm",
    "tất toán", "đáo hạn", "tiền gửi", "mở sổ", "rút trước hạn",
    "bảo hiểm tiền gửi", "hạn mức bảo hiểm", "kyc", "định danh khách hàng",
    "gốc", "lãi nhập gốc", "chào", "cảm ơn", "xin chào", "hello", "hi",
]

# --- Yêu cầu KHÔNG được phép trả lời dù có vẻ liên quan ---
UNSAFE_PATTERNS = [
    r"rửa tiền", r"trốn thuế", r"giấu tiền", r"lách luật",
    r"gian lận lãi suất", r"làm giả (sổ|giấy tờ|chứng từ)",
    r"cách (hack|xâm nhập|bẻ khóa)", r"lãi suất (chắc chắn|cam kết) \d+%",
]

# --- Câu hỏi đòi tư vấn đầu tư / tài chính cá nhân vượt phạm vi ---
FINANCIAL_ADVICE_PATTERNS = [
    r"nên gửi (bao nhiêu|ngân hàng nào)", r"đầu tư (gì|vào đâu)",
    r"có nên (gửi|rút|đầu tư)", r"ngân hàng nào (tốt nhất|uy tín nhất|lãi cao nhất)",
]

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
    r"bạn (bây giờ|từ giờ) là", r"you are now", r"act as (?!.*(nhân viên tư vấn))",
    r"jailbreak", r"DAN mode",
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
