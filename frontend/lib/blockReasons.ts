import type { BlockReason } from "@/types/chat";

export const BLOCK_REASON_LABELS: Record<BlockReason, string> = {
  none: "",
  out_of_scope: "Ngoài phạm vi",
  pii_detected: "Thông tin cá nhân nhạy cảm",
  unsafe_advice_request: "Yêu cầu tư vấn tài chính cá nhân",
  prompt_injection: "Yêu cầu không hợp lệ",
  input_too_long: "Câu hỏi quá dài",
  low_confidence_answer: "Không đủ dữ liệu",
};
