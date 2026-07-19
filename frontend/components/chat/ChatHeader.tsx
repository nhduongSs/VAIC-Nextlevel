import { ArrowRight } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

interface ChatHeaderProps {
  onGoToLogin: () => void;
}

export function ChatHeader({ onGoToLogin }: ChatHeaderProps) {
  return (
    <div className="flex items-center justify-between border-b border-border bg-card px-7 py-4">
      <div className="flex items-center gap-3">
        <Avatar className="h-9 w-9">
          <AvatarFallback className="text-[13px]">TL</AvatarFallback>
        </Avatar>
        <div className="flex flex-col leading-tight">
          <span className="text-[14.5px] font-bold">Trợ lý ảo NextBank</span>
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
            Đang hoạt động · Tư vấn điều khoản gửi tiền
          </span>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <p className="hidden max-w-[260px] text-right text-xs leading-tight text-muted-foreground sm:block">
          Thông tin mang tính tham khảo, vui lòng đối chiếu tại quầy giao dịch hoặc hotline.
        </p>
        <button
          type="button"
          onClick={onGoToLogin}
          className="inline-flex cursor-pointer items-center gap-1 whitespace-nowrap rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold hover:bg-muted"
        >
          Đăng nhập
          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
