from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.guardrails import rules

settings = get_settings()

REFUSAL_MESSAGE = (
    "Xin lỗi, tôi chỉ hỗ trợ các câu hỏi liên quan đến quy định ngân hàng NHNN. "
    "Bạn vui lòng đặt câu hỏi trong phạm vi này nhé."
)

SMALL_TALK_REPLIES: dict[str, str] = {
    "greeting": (
        "Chào bạn! Mình là trợ lý ảo NextBank, sẵn sàng hỗ trợ các câu hỏi về "
        "lãi suất, kỳ hạn và điều khoản gửi tiền tiết kiệm. Bạn muốn hỏi gì nào?"
    ),
    "thanks": (
        "Không có gì, rất vui được hỗ trợ bạn! Nếu còn thắc mắc về gửi tiền "
        "tiết kiệm, cứ hỏi mình nhé."
    ),
    "farewell": "Tạm biệt bạn! Hẹn gặp lại khi bạn cần hỗ trợ thêm về dịch vụ gửi tiền nhé.",
    "wellbeing": (
        "Mình vẫn hoạt động tốt, cảm ơn bạn đã hỏi thăm! Mình có thể giúp gì "
        "cho bạn về gửi tiền tiết kiệm không?"
    ),
    "identity": (
        "Mình là trợ lý ảo NextBank, hỗ trợ tra cứu quy định, lãi suất và điều "
        "khoản gửi tiền tiết kiệm. Bạn cứ đặt câu hỏi nhé!"
    ),
}


class GuardrailResult:
    def __init__(self, allowed: bool, reason: str = "none", message: str = ""):
        self.allowed = allowed
        self.reason = reason
        self.message = message


class GuardrailService:
    def check_input(self, message: str) -> GuardrailResult:
        text = message.strip()
        if len(text) > 4000:
            return GuardrailResult(False, "input_too_long", "Câu hỏi quá dài.")
        if rules.matches_any(text, rules.INJECTION_PATTERNS):
            return GuardrailResult(
                False, "prompt_injection", "Không thể thực hiện yêu cầu này."
            )
        if rules.matches_any(text, rules.UNSAFE_PATTERNS):
            return GuardrailResult(
                False, "unsafe_request", "Không hỗ trợ nội dung này."
            )
        if rules.contains_pii(text):
            return GuardrailResult(
                False,
                "pii_detected",
                "Vui lòng không gửi thông tin cá nhân nhạy cảm qua chat.",
            )
        return GuardrailResult(True)

    def check_small_talk(self, message: str) -> str | None:
        """Return a friendly canned reply for greetings/thanks/farewells/etc,
        or None if the message isn't small talk (i.e. should go through RAG)."""
        category = rules.match_small_talk(message)
        if category is None:
            return None
        return SMALL_TALK_REPLIES[category]

    def check_retrieval(self, chunks: list[Any]) -> GuardrailResult:
        if not chunks:
            return GuardrailResult(False, "out_of_scope", REFUSAL_MESSAGE)
        return GuardrailResult(True)

    def check_output(self, answer: str) -> str:
        risky = ["chắc chắn 100%", "cam kết lãi suất", "đảm bảo lợi nhuận"]
        for term in risky:
            if term in answer.lower():
                answer = answer.replace(term, "[đã lược bỏ cam kết không phù hợp]")
        return answer
