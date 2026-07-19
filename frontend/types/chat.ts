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
  source_doc_id: string;
  source_title: string;
  target_doc_id: string;
  target_title: string;
  confidence: number;
}

export interface TimelineEntry {
  document_id: string;
  document_title: string;
  doc_number: string | null;
  version: number;
  effective_date: string | null;
  issued_date: string | null;
  relation_type: string | null;
  is_current: boolean;
}

export interface ChatApiResponse {
  session_id: string;
  answer: string;
  sources: Source[];
  conflicts: Conflict[];
  timeline: TimelineEntry[];
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
  timeline?: TimelineEntry[];
  blockReason?: BlockReason;
}
