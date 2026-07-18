import { Calculator, Table2 } from "lucide-react";
import type { MessageKind } from "@/types/chat";

const QUICK_QUESTIONS = [
  "Điều kiện tất toán trước hạn",
  "Lãi suất có cố định không?",
  "Gửi online có gì khác gửi tại quầy?",
  "Số tiền gửi tối thiểu là bao nhiêu?",
];

interface QuickRepliesProps {
  disabled: boolean;
  onAsk: (question: string) => void;
  onInsertTool: (kind: Extract<MessageKind, "rate_table" | "calculator">) => void;
}

export function QuickReplies({ disabled, onAsk, onInsertTool }: QuickRepliesProps) {
  return (
    <div className="flex flex-wrap gap-2 px-7 pt-3.5">
      {QUICK_QUESTIONS.map((question) => (
        <button
          key={question}
          type="button"
          disabled={disabled}
          onClick={() => onAsk(question)}
          className="whitespace-nowrap rounded-full border border-border bg-card px-3.5 py-2 text-[13px] font-medium hover:bg-muted disabled:opacity-50"
        >
          {question}
        </button>
      ))}
      <button
        type="button"
        disabled={disabled}
        onClick={() => onInsertTool("rate_table")}
        className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-border bg-card px-3.5 py-2 text-[13px] font-medium hover:bg-muted disabled:opacity-50"
      >
        <Table2 className="h-3.5 w-3.5" aria-hidden="true" />
        Xem biểu lãi suất
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onInsertTool("calculator")}
        className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-border bg-card px-3.5 py-2 text-[13px] font-medium hover:bg-muted disabled:opacity-50"
      >
        <Calculator className="h-3.5 w-3.5" aria-hidden="true" />
        Tính lãi suất nhanh
      </button>
    </div>
  );
}
