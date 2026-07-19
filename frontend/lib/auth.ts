import type { AuthSession, LoginApiResponse } from "@/types/auth";

const STORAGE_KEY = "shb-auth-session";

export function loadAuthSession(): AuthSession | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    return null;
  }
}

export function saveAuthSession(response: LoginApiResponse): AuthSession {
  const session: AuthSession = { accessToken: response.access_token, user: response.user };
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  }
  return session;
}

export function clearAuthSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function getAuthToken(): string | null {
  return loadAuthSession()?.accessToken ?? null;
}
