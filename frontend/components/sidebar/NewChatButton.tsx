import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface NewChatButtonProps {
  onClick: () => void;
}

export function NewChatButton({ onClick }: NewChatButtonProps) {
  return (
    <Button onClick={onClick} className="w-full justify-start">
      <Plus className="h-4 w-4" aria-hidden="true" />
      Cuộc trò chuyện mới
    </Button>
  );
}
