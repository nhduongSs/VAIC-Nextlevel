import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
    <aside className="flex h-full w-[272px] flex-shrink-0 flex-col gap-4 border-r border-border bg-card p-4">
      <div className="flex items-center gap-2.5 px-1.5 pb-1">
        <div className="flex h-[38px] w-[38px] flex-shrink-0 items-center justify-center rounded-[11px] bg-primary text-[13px] font-extrabold text-primary-foreground">
          NB
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-[14.5px] font-bold">Trợ lý tiền gửi</span>
          <span className="text-xs text-muted-foreground">Tư vấn điều khoản gửi tiền</span>
        </div>
      </div>

      <NewChatButton onClick={onNewChat} />

      <SessionList sessions={sessions} activeSessionId={activeSessionId} onSelect={onSelectSession} />

      <div className="mt-auto flex items-center gap-2.5 border-t border-border pt-3">
        <Avatar className="h-[30px] w-[30px]">
          <AvatarFallback className="bg-muted text-[12px] text-muted-foreground">KH</AvatarFallback>
        </Avatar>
        <div className="flex flex-col leading-tight">
          <span className="text-[12.5px] font-semibold">Khách hàng</span>
          <span className="text-[11px] text-muted-foreground">Phiên tư vấn ẩn danh</span>
        </div>
      </div>
    </aside>
  );
}
