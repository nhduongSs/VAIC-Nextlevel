"use client";

import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { StoredSession } from "@/lib/sessions";

interface SessionListProps {
  sessions: StoredSession[];
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
}

export function SessionList({ sessions, activeSessionId, onSelect }: SessionListProps) {
  return (
    <ScrollArea className="flex-1">
      <div className="flex flex-col gap-0.5">
        <p className="px-2 pb-2 pt-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Lịch sử hội thoại
        </p>
        {sessions.map((session) => (
          <button
            key={session.id}
            type="button"
            onClick={() => onSelect(session.id)}
            className={cn(
              "rounded-[10px] px-2.5 py-2.5 text-left transition-colors hover:bg-muted",
              session.id === activeSessionId ? "bg-primary/10" : "bg-transparent"
            )}
          >
            <p
              className={cn(
                "truncate text-[13px] text-foreground",
                session.id === activeSessionId ? "font-bold" : "font-medium"
              )}
            >
              {session.title || "Cuộc trò chuyện mới"}
            </p>
            <p className="text-[11.5px] text-muted-foreground">{new Date(session.createdAt).toLocaleString("vi-VN")}</p>
          </button>
        ))}
      </div>
    </ScrollArea>
  );
}
