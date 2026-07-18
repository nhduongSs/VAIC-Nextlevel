from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """Bạn là trợ lý ảo CHỈ hỗ trợ khách hàng về quy định ngân hàng NHNN Việt Nam
(thông tư, quyết định, quy chế tín dụng, lãi suất cho vay, tiền gửi).

QUY TẮC BẮT BUỘC:
1. CHỈ trả lời dựa trên phần "NGỮ CẢNH" được cung cấp. Không tự suy đoán.
2. Nếu ngữ cảnh không đủ thông tin, nói rõ không có thông tin và đề nghị liên hệ NHNN.
3. Luôn ưu tiên văn bản có hiệu lực mới nhất.
4. Nếu có CẢNH BÁO MÂU THUẪN, PHẢI nêu rõ cho người dùng.
5. Khi trích dẫn, PHẢI nêu tên văn bản + điều khoản.
6. Văn phong: chuyên nghiệp, ngắn gọn, tiếng Việt.
"""


class LLMService:
    def __init__(self) -> None:
        cfg = get_settings()
        self._client = AsyncOpenAI(
            api_key=cfg.DEEPSEEK_API_KEY,
            base_url=cfg.DEEPSEEK_BASE_URL,
        )
        self._model = cfg.LLM_MODEL
        self._max_tokens = cfg.LLM_MAX_TOKENS
        self._temperature = cfg.LLM_TEMPERATURE

    async def generate_answer(
        self, question: str, context_block: str, conflict_block: str = ""
    ) -> str:
        user_content = (
            f"NGỮ CẢNH:\n{context_block}\n\n"
            f"CẢNH BÁO MÂU THUẪN:\n{conflict_block or '(không có)'}\n\n"
            f"CÂU HỎI:\n{question}"
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        return str(response.choices[0].message.content or "").strip()
