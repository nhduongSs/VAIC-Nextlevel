import { AlertTriangle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Conflict } from "@/types/chat";

interface ConflictNoticeProps {
  conflicts: Conflict[];
}

export function ConflictNotice({ conflicts }: ConflictNoticeProps) {
  if (conflicts.length === 0) return null;

  return (
    <Card className="flex flex-col gap-2 border-destructive/30 bg-destructive/5 p-3.5">
      <Badge variant="destructive" className="w-fit gap-1">
        <AlertTriangle className="h-3 w-3" aria-hidden="true" />
        Phát hiện mâu thuẫn
      </Badge>
      {conflicts.map((conflict, index) => (
        <div key={index} className="text-xs text-foreground">
          <p>{conflict.description}</p>
          <p className="mt-0.5 text-muted-foreground">
            Nguồn xung đột: {conflict.source_title} ⟷ {conflict.target_title}
          </p>
        </div>
      ))}
    </Card>
  );
}
