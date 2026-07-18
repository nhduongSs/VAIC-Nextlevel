import { NewChatButton } from "./NewChatButton";
import { SessionList } from "./SessionList";
import type { StoredSession } from "@/lib/sessions";

interface SidebarProps {
  sessions: StoredSession[];
  activeSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
}

export function Sidebar({ sessions, activeSessionId, onNewChat, onSelectSession }: SidebarProps) {
  return (
    <aside className="glass-card flex h-full w-72 flex-col gap-3 rounded-none border-r border-border p-3">
      <div className="flex items-center gap-2 px-1 py-2">
        <div className="h-8 w-8 rounded-lg bg-synapse-gradient" />
        <span className="text-sm font-semibold">SHB Trợ lý tiền gửi</span>
      </div>
      <NewChatButton onClick={onNewChat} />
      <SessionList sessions={sessions} activeSessionId={activeSessionId} onSelect={onSelectSession} />
    </aside>
  );
}
