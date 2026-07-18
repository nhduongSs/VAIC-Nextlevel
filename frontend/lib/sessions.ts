import type { Message } from "@/types/chat";

export interface StoredSession {
  id: string;
  title: string;
  createdAt: string;
  messages: Message[];
}

const STORAGE_KEY = "shb-chat-sessions";

export function loadSessions(): StoredSession[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as StoredSession[];
  } catch {
    return [];
  }
}

export function saveSessions(sessions: StoredSession[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function createSessionId(): string {
  return crypto.randomUUID();
}

export function upsertSession(sessions: StoredSession[], session: StoredSession): StoredSession[] {
  const index = sessions.findIndex((s) => s.id === session.id);
  if (index === -1) return [session, ...sessions];
  const next = [...sessions];
  next[index] = session;
  return next;
}

export function deriveTitle(firstMessage: string): string {
  const trimmed = firstMessage.trim();
  return trimmed.length > 40 ? `${trimmed.slice(0, 40)}...` : trimmed;
}
