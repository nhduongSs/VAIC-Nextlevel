import { FileText } from "lucide-react";
import type { Source } from "@/types/chat";

interface SourcePillProps {
  source: Source;
}

export function SourcePill({ source }: SourcePillProps) {
  return (
    <span className="inline-flex items-center gap-1.5 self-start rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground">
      <FileText className="h-3.5 w-3.5" aria-hidden="true" />
      Trích từ: <span className="font-bold text-primary">{source.title}</span>
    </span>
  );
}
