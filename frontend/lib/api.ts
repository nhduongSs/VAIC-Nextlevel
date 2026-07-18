import type { ChatApiResponse } from "@/types/chat";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 30000;

export class ChatApiError extends Error {}

export async function sendChatMessage(sessionId: string, message: string): Promise<ChatApiResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ChatApiError(`Máy chủ trả lỗi: ${response.status}`);
    }

    return (await response.json()) as ChatApiResponse;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ChatApiError("Hết thời gian chờ phản hồi từ máy chủ");
    }
    if (error instanceof ChatApiError) throw error;
    throw new ChatApiError("Không kết nối được máy chủ");
  } finally {
    clearTimeout(timeout);
  }
}
