"use client";

import { RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BLOCK_REASON_LABELS } from "@/lib/blockReasons";
import { SourcePill } from "./SourcePill";
import { ConflictNotice } from "./ConflictNotice";
import { DocumentTimeline } from "./DocumentTimeline";
import { RateTableCard } from "./RateTableCard";
import { InterestCalculatorCard } from "./InterestCalculatorCard";
import type { Message } from "@/types/chat";

interface MessageBubbleProps {
  message: Message;
  onRetry: () => void;
  isSending: boolean;
}

export function MessageBubble({ message, onRetry, isSending }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isBlocked = message.role === "blocked";
  const isError = message.role === "error";
  const isBotSide = !isUser;

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      {isBotSide && (
        <Avatar className="mt-0.5 h-8 w-8 flex-shrink-0">
          <AvatarFallback className="text-[11.5px]">TL</AvatarFallback>
        </Avatar>
      )}
      <div className={cn("flex max-w-[70%] flex-col gap-2.5", isUser && "items-end")}>
        {message.content && (
          <div
            className={cn(
              "px-4 py-3 text-[14.5px] leading-relaxed",
              isUser && "rounded-[16px_4px_16px_16px] bg-primary text-primary-foreground",
              !isUser && !isBlocked && !isError && "surface-card rounded-[4px_16px_16px_16px] text-foreground",
              isBlocked && "rounded-[4px_16px_16px_16px] border border-warning/40 bg-warning/10 text-warning-foreground",
              isError && "rounded-[4px_16px_16px_16px] border border-destructive/30 bg-destructive/5 text-destructive"
            )}
          >
            {isBlocked && message.blockReason && (
              <Badge variant="warning" className="mb-2">
                {BLOCK_REASON_LABELS[message.blockReason]}
              </Badge>
            )}
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
        )}

        {message.kind === "rate_table" && <RateTableCard />}
        {message.kind === "calculator" && <InterestCalculatorCard />}

        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.sources.map((source, index) => (
              <SourcePill key={`${source.doc_id}-${index}`} source={source} />
            ))}
          </div>
        )}

        {message.conflicts && message.conflicts.length > 0 && <ConflictNotice conflicts={message.conflicts} />}

        {message.timeline && message.timeline.length > 0 && <DocumentTimeline timeline={message.timeline} />}

        {isError && (
          <Button size="sm" variant="outline" onClick={onRetry} disabled={isSending}>
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            Thử lại
          </Button>
        )}
      </div>
    </div>
  );
}
