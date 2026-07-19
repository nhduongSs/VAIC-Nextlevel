import type { ChatApiResponse } from "@/types/chat";
import type { LoginApiResponse } from "@/types/auth";
import type { DocumentFormValues } from "@/lib/adminDocuments";
import { getAuthToken } from "@/lib/auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 30000;

export class ChatApiError extends Error {}
export class ApiError extends Error {}
export class AuthApiError extends Error {}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

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
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new ApiError(`Cập nhật tài liệu thất bại: ${response.status}`);
  return (await response.json()) as DocumentResponse;
}

export async function listDocuments(): Promise<DocumentResponse[]> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/documents?limit=100`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new ApiError(`Không tải được danh sách tài liệu: ${response.status}`);
  const body = (await response.json()) as PaginatedResponse<DocumentResponse>;
  return body.data;
}

export async function createDocument(file: File, values: DocumentFormValues): Promise<DocumentResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("title", values.name);
  form.append("doc_type", values.docType);
  form.append("authority_level", values.authorityLevel);
  if (values.docNumber) form.append("doc_number", values.docNumber);
  if (values.issuingBody) form.append("issuing_body", values.issuingBody);
  if (values.issuedDate) form.append("issued_date", values.issuedDate);
  if (values.effectiveDate) form.append("effective_date", values.effectiveDate);
  if (values.expiredDate) form.append("expired_date", values.expiredDate);

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/documents`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!response.ok) throw new ApiError(`Tải tài liệu thất bại: ${response.status}`);
  const created = (await response.json()) as DocumentResponse;

  // Category (nhóm sản phẩm nội bộ, không có cột riêng phía backend) lưu như một tag.
  return patchDocument(created.id, { tags: values.category ? [values.category] : [] });
}

export async function updateDocument(id: string, values: DocumentFormValues): Promise<DocumentResponse> {
  return patchDocument(id, {
    title: values.name,
    tags: values.category ? [values.category] : [],
    doc_type: values.docType,
    authority_level: values.authorityLevel,
    doc_number: values.docNumber || null,
    issuing_body: values.issuingBody || null,
    issued_date: values.issuedDate || null,
    effective_date: values.effectiveDate || null,
    expired_date: values.expiredDate || null,
  });
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/documents/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (response.ok || response.status === 204) return;

  if (response.status === 403) {
    throw new ApiError("Tài khoản của bạn không có quyền xóa tài liệu.");
  }
  if (response.status === 401) {
    throw new ApiError("Vui lòng đăng nhập lại để thực hiện thao tác này.");
  }
  throw new ApiError(`Xóa tài liệu thất bại: ${response.status}`);
}

export async function login(email: string, password: string): Promise<LoginApiResponse> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new AuthApiError("Email hoặc mật khẩu không đúng");
    }
    throw new AuthApiError(`Đăng nhập thất bại: ${response.status}`);
  }

  return (await response.json()) as LoginApiResponse;
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
