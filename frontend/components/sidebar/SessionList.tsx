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
      <div className="flex flex-col gap-1 p-2">
        {sessions.map((session) => (
          <button
            key={session.id}
            type="button"
            onClick={() => onSelect(session.id)}
            className={cn(
              "rounded-md px-3 py-2 text-left text-sm text-muted-foreground transition-colors hover:bg-muted",
              session.id === activeSessionId && "bg-muted text-foreground"
            )}
          >
            <p className="truncate font-medium">{session.title || "Cuộc trò chuyện mới"}</p>
            <p className="text-xs text-muted-foreground">{new Date(session.createdAt).toLocaleString("vi-VN")}</p>
          </button>
        ))}
      </div>
    </ScrollArea>
  );
}
