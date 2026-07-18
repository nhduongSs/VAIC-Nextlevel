export type BlockReason =
  | "none"
  | "out_of_scope"
  | "pii_detected"
  | "unsafe_advice_request"
  | "prompt_injection"
  | "input_too_long"
  | "low_confidence_answer";

export interface Source {
  doc_id: string;
  title: string;
  clause: string;
  effective_date: string;
}

export interface Conflict {
  description: string;
  conflicting_sources: string[];
}

export interface ChatApiResponse {
  session_id: string;
  answer: string;
  sources: Source[];
  conflicts: Conflict[];
  blocked: boolean;
  block_reason: BlockReason;
}

export type MessageRole = "user" | "assistant" | "blocked" | "error";

export type MessageKind = "text" | "rate_table" | "calculator";

export interface Message {
  id: string;
  role: MessageRole;
  kind?: MessageKind;
  content: string;
  createdAt: string;
  sources?: Source[];
  conflicts?: Conflict[];
  blockReason?: BlockReason;
}
