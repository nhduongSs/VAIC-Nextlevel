import type { ChatApiResponse } from "@/types/chat";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 30000;

// Admin uploads don't collect legal-document classification (doc_type / authority_level) —
// bank product docs default to these two values.
const DOC_DEFAULT_DOC_TYPE = "PRODUCT_DOC";
const DOC_DEFAULT_AUTHORITY_LEVEL = "INTERNAL_POLICY";

export class ChatApiError extends Error {}
export class ApiError extends Error {}

export interface DocumentResponse {
  id: string;
  title: string;
  filename: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  status: string;
  version: number;
  doc_type: string;
  authority_level: string;
  doc_number: string | null;
  issuing_body: string | null;
  issued_date: string | null;
  effective_date: string | null;
  expired_date: string | null;
  tags: string[];
  metadata_extra: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

interface PaginatedResponse<T> {
  data: T[];
  meta: { total: number; limit: number; offset: number; has_next: boolean; has_prev: boolean };
}

async function fetchWithTimeout(url: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Hết thời gian chờ phản hồi từ máy chủ");
    }
    throw new ApiError("Không kết nối được máy chủ");
  } finally {
    clearTimeout(timeout);
  }
}

async function patchDocument(id: string, body: Record<string, unknown>): Promise<DocumentResponse> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/documents/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new ApiError(`Cập nhật tài liệu thất bại: ${response.status}`);
  return (await response.json()) as DocumentResponse;
}

export async function listDocuments(): Promise<DocumentResponse[]> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/documents?limit=100`);
  if (!response.ok) throw new ApiError(`Không tải được danh sách tài liệu: ${response.status}`);
  const body = (await response.json()) as PaginatedResponse<DocumentResponse>;
  return body.data;
}

export async function createDocument(file: File, title: string, category: string): Promise<DocumentResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title);
  form.append("doc_type", DOC_DEFAULT_DOC_TYPE);
  form.append("authority_level", DOC_DEFAULT_AUTHORITY_LEVEL);

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/documents`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) throw new ApiError(`Tải tài liệu thất bại: ${response.status}`);
  const created = (await response.json()) as DocumentResponse;

  // Category has no matching field on the backend document schema — stored as a tag.
  return patchDocument(created.id, { tags: [category] });
}

export async function updateDocument(
  id: string,
  values: { title: string; category: string },
): Promise<DocumentResponse> {
  return patchDocument(id, { title: values.title, tags: [values.category] });
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/documents/${id}`, {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 204) {
    throw new ApiError(`Xóa tài liệu thất bại: ${response.status}`);
  }
}

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
