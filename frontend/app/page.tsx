"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { LoginView } from "@/components/login/LoginView";
import { AdminDashboardView } from "@/components/admin/AdminDashboardView";
import { sendChatMessage, ChatApiError } from "@/lib/api";
import {
  createSessionId,
  deriveTitle,
  loadSessions,
  saveSessions,
  upsertSession,
  type StoredSession,
} from "@/lib/sessions";
import type { Message, MessageKind } from "@/types/chat";

type View = "chat" | "login" | "dashboard";

const TOOL_MESSAGE_INTRO: Record<Extract<MessageKind, "rate_table" | "calculator">, string> = {
  rate_table: "Dạ, đây là biểu lãi suất tiền gửi tiết kiệm tham khảo theo từng kỳ hạn:",
  calculator: "Anh/chị có thể dùng công cụ tính lãi nhanh bên dưới để ước tính số tiền lãi nhận được ạ.",
};

function lastMessageOfRole(session: StoredSession | undefined, role: Message["role"]) {
  if (!session) return null;
  return [...session.messages].reverse().find((m) => m.role === role) ?? null;
}

export default function HomePage() {
  const [view, setView] = useState<View>("chat");
  const [adminEmail, setAdminEmail] = useState("");
  const [sessions, setSessions] = useState<StoredSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    const stored = loadSessions();
    setSessions(stored);
    if (stored.length > 0) setActiveSessionId(stored[0].id);
  }, []);

  function updateSessions(updater: (prev: StoredSession[]) => StoredSession[]) {
    setSessions((prev) => {
      const next = updater(prev);
      saveSessions(next);
      return next;
    });
  }

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  function handleNewChat() {
    setActiveSessionId(createSessionId());
  }

  function handleSelectSession(sessionId: string) {
    setActiveSessionId(sessionId);
  }

  function appendMessage(sessionId: string, message: Message, seedTitle: string) {
    updateSessions((prev) => {
      const existing = prev.find((s) => s.id === sessionId);
      const updatedSession: StoredSession = existing
        ? { ...existing, messages: [...existing.messages, message] }
        : { id: sessionId, title: deriveTitle(seedTitle), createdAt: new Date().toISOString(), messages: [message] };
      return upsertSession(prev, updatedSession);
    });
  }

  async function callApiAndAppend(sessionId: string, text: string) {
    setIsSending(true);
    try {
      const response = await sendChatMessage(sessionId, text);
      const replyMessage: Message = response.blocked
        ? {
            id: crypto.randomUUID(),
            role: "blocked",
            content: response.answer,
            createdAt: new Date().toISOString(),
            blockReason: response.block_reason,
          }
        : {
            id: crypto.randomUUID(),
            role: "assistant",
            content: response.answer,
            createdAt: new Date().toISOString(),
            sources: response.sources,
            conflicts: response.conflicts,
          };
      appendMessage(sessionId, replyMessage, text);
    } catch (error) {
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: "error",
        content: error instanceof ChatApiError ? error.message : "Đã có lỗi không xác định xảy ra",
        createdAt: new Date().toISOString(),
      };
      appendMessage(sessionId, errorMessage, text);
    } finally {
      setIsSending(false);
    }
  }

  async function handleSend(text: string) {
    const sessionId = activeSessionId ?? createSessionId();
    setActiveSessionId(sessionId);

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      createdAt: new Date().toISOString(),
    };
    appendMessage(sessionId, userMessage, text);

    await callApiAndAppend(sessionId, text);
  }

  async function handleRetry() {
    if (!activeSession) return;
    const lastUserMessage = lastMessageOfRole(activeSession, "user");
    if (!lastUserMessage) return;
    await callApiAndAppend(activeSession.id, lastUserMessage.content);
  }

  function handleInsertTool(kind: Extract<MessageKind, "rate_table" | "calculator">) {
    const sessionId = activeSessionId ?? createSessionId();
    setActiveSessionId(sessionId);
    const toolMessage: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      kind,
      content: TOOL_MESSAGE_INTRO[kind],
      createdAt: new Date().toISOString(),
    };
    appendMessage(sessionId, toolMessage, TOOL_MESSAGE_INTRO[kind]);
  }

  if (view === "login") {
    return (
      <LoginView
        onLoginSuccess={(email) => {
          setAdminEmail(email);
          setView("dashboard");
        }}
        onBackToChat={() => setView("chat")}
      />
    );
  }

  if (view === "dashboard") {
    return (
      <AdminDashboardView
        adminEmail={adminEmail}
        onLogout={() => {
          setAdminEmail("");
          setView("chat");
        }}
        onGoToChat={() => setView("chat")}
      />
    );
  }

  return (
    <main className="flex h-screen overflow-hidden">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
      />
      <ChatWindow
        messages={activeSession?.messages ?? []}
        isSending={isSending}
        onSend={handleSend}
        onRetry={handleRetry}
        onInsertTool={handleInsertTool}
        onGoToLogin={() => setView("login")}
      />
    </main>
  );
}
