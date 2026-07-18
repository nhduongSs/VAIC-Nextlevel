import { FileText, LogOut } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";

interface AdminSidebarProps {
  adminEmail: string;
  onLogout: () => void;
  onGoToChat: () => void;
}

export function AdminSidebar({ adminEmail, onLogout, onGoToChat }: AdminSidebarProps) {
  return (
    <aside className="flex h-full w-[250px] flex-shrink-0 flex-col border-r border-border bg-card p-4">
      <div className="flex items-center gap-2.5 px-1.5 pb-5">
        <div className="flex h-[38px] w-[38px] flex-shrink-0 items-center justify-center rounded-[11px] bg-primary text-[13px] font-extrabold text-primary-foreground">
          SHB
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-[14.5px] font-bold">Quản trị</span>
          <span className="text-xs text-muted-foreground">Bảng điều khiển nội dung</span>
        </div>
      </div>

      <div className="flex items-center gap-2.5 rounded-[10px] bg-primary/10 px-3 py-2.5 text-[13.5px] font-bold">
        <FileText className="h-4 w-4 text-primary" aria-hidden="true" />
        Tài liệu điều khoản
      </div>

      <div className="mt-auto flex flex-col gap-2 border-t border-border pt-3">
        <div className="flex items-center gap-2.5">
          <Avatar className="h-[30px] w-[30px]">
            <AvatarFallback className="bg-muted text-[12px] text-muted-foreground">AD</AvatarFallback>
          </Avatar>
          <div className="flex flex-col leading-tight">
            <span className="truncate text-[12.5px] font-semibold">{adminEmail}</span>
            <span className="text-[11px] text-muted-foreground">Quản trị viên</span>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={onLogout} className="w-full justify-center">
          <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
          Đăng xuất
        </Button>
        <button
          type="button"
          onClick={onGoToChat}
          className="cursor-pointer text-center text-xs text-muted-foreground hover:text-foreground"
        >
          Xem giao diện Chat →
        </button>
      </div>
    </aside>
  );
}
