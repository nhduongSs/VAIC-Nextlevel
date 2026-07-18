"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import type { Message } from "@/types/chat";

interface MessageListProps {
  messages: Message[];
  isSending: boolean;
  selectedMessageId: string | null;
  onSelectMessage: (messageId: string) => void;
  onRetry: () => void;
}

export function MessageList({ messages, isSending, selectedMessageId, onSelectMessage, onRetry }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isSending]);

  return (
    <ScrollArea className="flex-1 px-4">
      <div className="flex flex-col gap-4 py-4">
        {messages.length === 0 && (
          <p className="mt-10 text-center text-sm text-muted-foreground">
            Bắt đầu hỏi về lãi suất, kỳ hạn, điều khoản tiền gửi SHB.
          </p>
        )}
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            isSelected={message.id === selectedMessageId}
            onSelect={onSelectMessage}
            onRetry={onRetry}
            isSending={isSending}
          />
        ))}
        {isSending && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
