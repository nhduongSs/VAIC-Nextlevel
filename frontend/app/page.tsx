"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { InsightsPanel } from "@/components/insights/InsightsPanel";
import { sendChatMessage, ChatApiError } from "@/lib/api";
import {
  createSessionId,
  deriveTitle,
  loadSessions,
  saveSessions,
  upsertSession,
  type StoredSession,
} from "@/lib/sessions";
import type { Message } from "@/types/chat";

function lastMessageOfRole(session: StoredSession | undefined, role: Message["role"]) {
  if (!session) return null;
  return [...session.messages].reverse().find((m) => m.role === role) ?? null;
}

export default function HomePage() {
  const [sessions, setSessions] = useState<StoredSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    const stored = loadSessions();
    setSessions(stored);
    if (stored.length > 0) {
      setActiveSessionId(stored[0].id);
      setSelectedMessageId(lastMessageOfRole(stored[0], "assistant")?.id ?? null);
    }
  }, []);

  function updateSessions(updater: (prev: StoredSession[]) => StoredSession[]) {
    setSessions((prev) => {
      const next = updater(prev);
      saveSessions(next);
      return next;
    });
  }

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const selectedMessage = activeSession?.messages.find((m) => m.id === selectedMessageId) ?? null;

  function handleNewChat() {
    setActiveSessionId(createSessionId());
    setSelectedMessageId(null);
  }

  function handleSelectSession(sessionId: string) {
    setActiveSessionId(sessionId);
    const session = sessions.find((s) => s.id === sessionId);
    setSelectedMessageId(lastMessageOfRole(session, "assistant")?.id ?? null);
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
      if (!response.blocked) setSelectedMessageId(replyMessage.id);
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
        selectedMessageId={selectedMessageId}
        onSelectMessage={setSelectedMessageId}
        onSend={handleSend}
        onRetry={handleRetry}
      />
      <InsightsPanel selectedMessage={selectedMessage} />
    </main>
  );
}
