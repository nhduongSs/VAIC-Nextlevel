"use client";

import { useState, type KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

interface MessageInputProps {
  disabled: boolean;
  onSend: (message: string) => void;
}

export function MessageInput({ disabled, onSend }: MessageInputProps) {
  const [value, setValue] = useState("");

  function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="px-7 pb-6 pt-4">
      <div className="flex items-end gap-2.5 rounded-2xl border border-border bg-card p-2 pl-4">
        <Textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Nhập câu hỏi về điều khoản gửi tiền..."
          rows={1}
          className="flex-1 resize-none border-none bg-transparent px-0 py-2 shadow-none focus-visible:ring-0"
        />
        <Button onClick={handleSubmit} disabled={disabled || !value.trim()}>
          Gửi
          <Send className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
      <p className="pt-2.5 text-center text-[11.5px] text-muted-foreground">
        Trợ lý AI có thể cung cấp thông tin chưa chính xác tuyệt đối. Vui lòng xác nhận lại tại quầy giao dịch hoặc
        tổng đài trước khi quyết định.
      </p>
    </div>
  );
}
