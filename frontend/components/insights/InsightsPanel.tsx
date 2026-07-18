import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { SourcesTab } from "./SourcesTab";
import { ConflictsTab } from "./ConflictsTab";
import type { Message } from "@/types/chat";

interface InsightsPanelProps {
  selectedMessage: Message | null;
}

export function InsightsPanel({ selectedMessage }: InsightsPanelProps) {
  const sources = selectedMessage?.sources ?? [];
  const conflicts = selectedMessage?.conflicts ?? [];

  return (
    <aside className="glass-card flex h-full w-80 flex-col rounded-none border-l border-border p-3">
      <p className="px-1 py-2 text-sm font-semibold">Thông tin trích dẫn</p>
      <Tabs defaultValue="sources" className="flex flex-1 flex-col">
        <TabsList>
          <TabsTrigger value="sources">Nguồn trích dẫn</TabsTrigger>
          <TabsTrigger value="conflicts" className="relative">
            Mâu thuẫn
            {conflicts.length > 0 && (
              <Badge variant="destructive" className="ml-1.5 px-1.5 py-0">
                {conflicts.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>
        <TabsContent value="sources" className="flex-1 overflow-y-auto">
          <SourcesTab sources={sources} />
        </TabsContent>
        <TabsContent value="conflicts" className="flex-1 overflow-y-auto">
          <ConflictsTab conflicts={conflicts} />
        </TabsContent>
      </Tabs>
    </aside>
  );
}
