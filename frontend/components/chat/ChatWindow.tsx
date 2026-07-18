import { ChatHeader } from "./ChatHeader";
import { MessageList } from "./MessageList";
import { QuickReplies } from "./QuickReplies";
import { MessageInput } from "./MessageInput";
import type { Message, MessageKind } from "@/types/chat";

interface ChatWindowProps {
  messages: Message[];
  isSending: boolean;
  onSend: (message: string) => void;
  onRetry: () => void;
  onInsertTool: (kind: Extract<MessageKind, "rate_table" | "calculator">) => void;
  onGoToLogin: () => void;
}

export function ChatWindow({ messages, isSending, onSend, onRetry, onInsertTool, onGoToLogin }: ChatWindowProps) {
  return (
    <section className="flex h-full flex-1 flex-col bg-background">
      <ChatHeader onGoToLogin={onGoToLogin} />
      <MessageList messages={messages} isSending={isSending} onRetry={onRetry} />
      <QuickReplies disabled={isSending} onAsk={onSend} onInsertTool={onInsertTool} />
      <MessageInput disabled={isSending} onSend={onSend} />
    </section>
  );
}
