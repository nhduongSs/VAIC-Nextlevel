import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import type { Message } from "@/types/chat";

interface ChatWindowProps {
  messages: Message[];
  isSending: boolean;
  selectedMessageId: string | null;
  onSelectMessage: (messageId: string) => void;
  onSend: (message: string) => void;
  onRetry: () => void;
}

export function ChatWindow({ messages, isSending, selectedMessageId, onSelectMessage, onSend, onRetry }: ChatWindowProps) {
  return (
    <section className="flex h-full flex-1 flex-col">
      <MessageList
        messages={messages}
        isSending={isSending}
        selectedMessageId={selectedMessageId}
        onSelectMessage={onSelectMessage}
        onRetry={onRetry}
      />
      <MessageInput disabled={isSending} onSend={onSend} />
    </section>
  );
}
