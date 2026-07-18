import { Card } from "@/components/ui/card";
import type { Source } from "@/types/chat";

interface SourcesTabProps {
  sources: Source[];
}

export function SourcesTab({ sources }: SourcesTabProps) {
  if (sources.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">Chưa có nguồn trích dẫn nào.</p>;
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      {sources.map((source, index) => (
        <Card key={`${source.doc_id}-${index}`} className="p-3">
          <p className="text-sm font-medium">{source.title}</p>
          <p className="text-xs text-muted-foreground">{source.clause}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Hiệu lực: {source.effective_date} · Mã: {source.doc_id}
          </p>
        </Card>
      ))}
    </div>
  );
}
