"""
Guardrail Service — lớp kiểm soát hành vi & lời nói của AI.

Kiến trúc 2 lớp:
1. Input guard  : chặn trước khi gọi LLM (rẻ, nhanh, rule-based)
2. Output guard : kiểm tra sau khi LLM trả lời, trước khi gửi cho user
"""

from app.core.config import get_settings
from app.core.logging import log_conversation
from app.guardrails import rules
from app.models.schemas import BlockReason, RetrievedChunk

settings = get_settings()

REFUSAL_MESSAGE = (
    "Xin lỗi, tôi chỉ hỗ trợ các câu hỏi liên quan đến dịch vụ tiền gửi "
    "(tiết kiệm, lãi suất, kỳ hạn, bảo hiểm tiền gửi, KYC...). "
    "Bạn vui lòng đặt câu hỏi trong phạm vi này nhé."
)

ADVICE_REDIRECT_MESSAGE = (
    "Tôi không thể tư vấn nên gửi tiền ở ngân hàng nào hay số tiền cụ thể, "
    "vì đây là quyết định tài chính cá nhân. "
    "Tôi có thể cung cấp thông tin lãi suất, điều kiện, quy định để bạn tự quyết định. "
    "Bạn cần tôi cung cấp thông tin gì cụ thể?"
)

PII_WARNING_MESSAGE = (
    "Tôi nhận thấy tin nhắn có thể chứa thông tin cá nhân nhạy cảm "
    "(số CCCD/tài khoản/điện thoại). Vì lý do bảo mật, bạn vui lòng KHÔNG "
    "gửi các thông tin này qua kênh chat. Tôi vẫn có thể hỗ trợ nếu bạn "
    "đặt lại câu hỏi mà không kèm thông tin cá nhân."
)


class GuardrailResult:
    def __init__(self, allowed: bool, reason: BlockReason = BlockReason.NONE, message: str = ""):
        self.allowed = allowed
        self.reason = reason
        self.message = message


class GuardrailService:
    def check_input(self, session_id: str, message: str) -> GuardrailResult:
        text = message.strip()

        if len(text) > settings.max_input_length:
            return self._blocked(
                session_id, message, BlockReason.INPUT_TOO_LONG, "Câu hỏi quá dài, bạn vui lòng rút gọn giúp tôi."
            )

        if rules.matches_any(text, rules.INJECTION_PATTERNS):
            return self._blocked(
                session_id,
                message,
                BlockReason.PROMPT_INJECTION,
                "Tôi không thể thực hiện yêu cầu thay đổi vai trò/hướng dẫn hệ thống.",
            )

        if rules.matches_any(text, rules.UNSAFE_PATTERNS):
            return self._blocked(
                session_id, message, BlockReason.UNSAFE_ADVICE_REQUEST, "Tôi không thể hỗ trợ nội dung này."
            )

        pii_found = rules.contains_pii(text)
        if pii_found:
            return self._blocked(session_id, message, BlockReason.PII_DETECTED, PII_WARNING_MESSAGE)

        if rules.matches_any(text, rules.FINANCIAL_ADVICE_PATTERNS):
            return self._blocked(session_id, message, BlockReason.UNSAFE_ADVICE_REQUEST, ADVICE_REDIRECT_MESSAGE)

        return GuardrailResult(allowed=True)

    def check_retrieval(self, chunks: list[RetrievedChunk]) -> GuardrailResult:
        """Nếu không tìm được context liên quan đủ tốt -> không cho LLM tự bịa,
        trả lời an toàn thay vì hallucinate."""
        if not chunks or all(c.score < settings.similarity_threshold for c in chunks):
            return GuardrailResult(
                allowed=False,
                reason=BlockReason.OUT_OF_SCOPE,
                message=REFUSAL_MESSAGE,
            )
        return GuardrailResult(allowed=True)

    def check_output(self, answer: str) -> str:
        """Hậu kiểm câu trả lời LLM sinh ra. Chặn các cam kết tuyệt đối
        (rủi ro pháp lý/uy tín)."""
        risky_terms = ["chắc chắn 100%", "cam kết lãi suất", "đảm bảo lợi nhuận", "bảo đảm sinh lời"]
        for term in risky_terms:
            if term in answer.lower():
                answer = answer.replace(term, "[đã lược bỏ nội dung cam kết không phù hợp]")
        return answer

    def _blocked(self, session_id: str, original: str, reason: BlockReason, message: str) -> GuardrailResult:
        if settings.log_blocked_requests:
            log_conversation(session_id, "SYSTEM_BLOCK", original, meta={"reason": reason})
        return GuardrailResult(allowed=False, reason=reason, message=message)
