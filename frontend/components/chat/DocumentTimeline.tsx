import { History } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { TimelineEntry } from "@/types/chat";

interface DocumentTimelineProps {
  timeline: TimelineEntry[];
}

function formatDate(value: string | null): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("vi-VN");
}

export function DocumentTimeline({ timeline }: DocumentTimelineProps) {
  if (timeline.length === 0) return null;

  return (
    <Card className="flex flex-col gap-2 border-border bg-card/60 p-3.5">
      <Badge className="w-fit gap-1">
        <History className="h-3 w-3" aria-hidden="true" />
        Lịch sử hiệu lực văn bản
      </Badge>
      <ol className="flex flex-col gap-2">
        {timeline.map((entry) => {
          const effectiveDate = formatDate(entry.effective_date);
          const issuedDate = formatDate(entry.issued_date);
          return (
            <li
              key={entry.document_id}
              className={cn(
                "flex flex-col gap-0.5 border-l-2 pl-3 text-xs",
                entry.is_current ? "border-primary" : "border-border text-muted-foreground"
              )}
            >
              <div className="flex flex-wrap items-center gap-1.5">
                <span className={cn("font-bold", entry.is_current ? "text-primary" : "text-foreground")}>
                  {entry.document_title}
                </span>
                <span>· v{entry.version}</span>
                {entry.doc_number && <span>· {entry.doc_number}</span>}
                {entry.is_current && (
                  <Badge variant="default" className="py-0">
                    Đang hiệu lực
                  </Badge>
                )}
              </div>
              {(effectiveDate || issuedDate) && (
                <div className="text-muted-foreground">
                  {issuedDate && <span>Ban hành: {issuedDate}</span>}
                  {issuedDate && effectiveDate && <span> · </span>}
                  {effectiveDate && <span>Hiệu lực: {effectiveDate}</span>}
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
