import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Conflict } from "@/types/chat";

interface ConflictsTabProps {
  conflicts: Conflict[];
}

export function ConflictsTab({ conflicts }: ConflictsTabProps) {
  if (conflicts.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">Không phát hiện mâu thuẫn nào.</p>;
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      {conflicts.map((conflict, index) => (
        <Card key={index} className="p-3">
          <Badge variant="destructive" className="mb-2">
            Mâu thuẫn
          </Badge>
          <p className="text-sm">{conflict.description}</p>
          <p className="mt-1 text-xs text-muted-foreground">Nguồn xung đột: {conflict.conflicting_sources.join(", ")}</p>
        </Card>
      ))}
    </div>
  );
}
