"use client";

import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BLOCK_REASON_LABELS } from "@/lib/blockReasons";
import type { Message } from "@/types/chat";

interface MessageBubbleProps {
  message: Message;
  isSelected: boolean;
  onSelect: (messageId: string) => void;
  onRetry: () => void;
  isSending: boolean;
}

export function MessageBubble({ message, isSelected, onSelect, onRetry, isSending }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isBlocked = message.role === "blocked";
  const isError = message.role === "error";
  const isAssistant = message.role === "assistant";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <Avatar>
        <AvatarFallback>{isUser ? "B" : "AI"}</AvatarFallback>
      </Avatar>
      <div className={cn("flex max-w-[75%] flex-col gap-1", isUser && "items-end")}>
        <button
          type="button"
          disabled={!isAssistant}
          onClick={() => isAssistant && onSelect(message.id)}
          className={cn(
            "rounded-lg px-4 py-2.5 text-left text-sm leading-relaxed",
            isUser && "bg-synapse-gradient text-white",
            isAssistant && "glass-card cursor-pointer text-foreground",
            isAssistant && isSelected && "ring-1 ring-primary",
            isBlocked && "border border-warning/40 bg-warning/10 text-warning-foreground",
            isError && "border border-destructive/40 bg-destructive/10 text-destructive"
          )}
        >
          {isBlocked && message.blockReason && (
            <Badge variant="warning" className="mb-2">
              {BLOCK_REASON_LABELS[message.blockReason]}
            </Badge>
          )}
          <p>{message.content}</p>
        </button>
        {isError && (
          <Button size="sm" variant="outline" onClick={onRetry} disabled={isSending}>
            Thử lại
          </Button>
        )}
      </div>
    </div>
  );
}
