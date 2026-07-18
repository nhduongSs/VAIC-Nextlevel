import { Button } from "@/components/ui/button";

interface NewChatButtonProps {
  onClick: () => void;
}

export function NewChatButton({ onClick }: NewChatButtonProps) {
  return (
    <Button onClick={onClick} className="w-full justify-start">
      + Cuộc trò chuyện mới
    </Button>
  );
}
