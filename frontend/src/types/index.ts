export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  role: "user" | "admin" | "moderator";
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Citation {
  document_id: string;
  document_name: string;
  chunk_text: string;
  page_number?: number;
  score: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  citations?: Citation[];
  tool_calls?: ToolCall[];
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  model_used?: string;
  latency_ms?: number;
  created_at: string;
  // Client-side only
  isStreaming?: boolean;
}

export interface ToolCall {
  tool: string;
  input: string;
  output: string;
}

export interface Conversation {
  id: string;
  title?: string;
  summary?: string;
  model_used?: string;
  total_tokens: number;
  total_cost_usd: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages?: Message[];
}

export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed";
  chunk_count: number;
  is_public: boolean;
  created_at: string;
  processed_at?: string;
  error_message?: string;
}

export interface Feedback {
  id: string;
  message_id: string;
  rating: "thumbs_up" | "thumbs_down";
  comment?: string;
  status: "pending" | "approved" | "rejected" | "in_dataset";
  created_at: string;
}

export interface StreamChunk {
  type: "token" | "citation" | "tool_call" | "done" | "error";
  content?: string;
  citations?: Citation[];
  tool_name?: string;
  tool_result?: unknown;
  message_id?: string;
  conversation_id?: string;
  error?: string;
}

export interface AdminMetrics {
  users: { total: number; active: number };
  conversations: { total: number; total_messages: number };
  documents: { total: number };
  ai_usage: { total_tokens: number; total_cost_usd: number };
  feedback: { total: number; positive: number; satisfaction_rate: number };
}
