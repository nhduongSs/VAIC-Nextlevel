import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <Avatar className="mt-0.5 h-8 w-8 flex-shrink-0">
        <AvatarFallback className="text-[11.5px]">TL</AvatarFallback>
      </Avatar>
      <div className="surface-card flex items-center gap-1.5 rounded-[4px_16px_16px_16px] px-4 py-3.5">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
      </div>
    </div>
  );
}
