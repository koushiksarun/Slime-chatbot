/**
 * API client — wraps axios with JWT auth, token refresh, and typed responses.
 * All requests go through Next.js rewrites (/api/backend/...) to avoid CORS.
 */
import axios, { AxiosInstance, AxiosError } from "axios";
import type { AuthTokens, Conversation, Message, Document, Feedback, AdminMetrics, StreamChunk } from "@/types";

const BASE_URL = "/api/backend";

function createClient(): AxiosInstance {
  const client = axios.create({
    baseURL: BASE_URL,
    headers: { "Content-Type": "application/json" },
    timeout: 30000,
  });

  // Attach access token from localStorage
  client.interceptors.request.use((config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // On 401 — try refresh token, then redirect to login
  client.interceptors.response.use(
    (res) => res,
    async (error: AxiosError) => {
      const original = error.config as any;
      if (error.response?.status === 401 && !original._retry) {
        original._retry = true;
        try {
          const refresh = localStorage.getItem("refresh_token");
          if (!refresh) throw new Error("No refresh token");
          const { data } = await axios.post<AuthTokens>(`${BASE_URL}/auth/refresh`, {
            refresh_token: refresh,
          });
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return client(original);
        } catch {
          localStorage.clear();
        }
      }
      return Promise.reject(error);
    }
  );

  return client;
}

export const apiClient = createClient();

// ── Auth ──────────────────────────────────────────────────────────────────────

export const auth = {
  register: (data: { email: string; username: string; password: string; full_name?: string }) =>
    apiClient.post<AuthTokens>("/auth/register", data).then((r) => r.data),

  login: (data: { email: string; password: string }) =>
    apiClient.post<AuthTokens>("/auth/login", data).then((r) => r.data),

  me: () => apiClient.get<AuthTokens["user"]>("/auth/me").then((r) => r.data),
};

// ── Chat ──────────────────────────────────────────────────────────────────────

export const chat = {
  sendMessage: (data: {
    message: string;
    conversation_id?: string;
    use_rag?: boolean;
    use_agents?: boolean;
    document_ids?: string[];
    stream?: boolean;
  }) => apiClient.post<Message>("/chat/", { ...data, stream: false }).then((r) => r.data),

  listConversations: (page = 1) =>
    apiClient.get<Conversation[]>(`/chat/conversations?page=${page}`).then((r) => r.data),

  getConversation: (id: string) =>
    apiClient.get<Conversation & { messages: Message[] }>(`/chat/conversations/${id}`).then((r) => r.data),

  deleteConversation: (id: string) =>
    apiClient.delete(`/chat/conversations/${id}`),
};

// ── Streaming ─────────────────────────────────────────────────────────────────

export async function* streamChat(params: {
  message: string;
  conversation_id?: string;
  use_rag?: boolean;
  use_agents?: boolean;
  document_ids?: string[];
}): AsyncGenerator<StreamChunk> {
  const token = localStorage.getItem("access_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}/chat/`, {
    method: "POST",
    headers,
    body: JSON.stringify({ ...params, stream: true }),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.statusText}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const chunk: StreamChunk = JSON.parse(line.slice(6));
          yield chunk;
          if (chunk.type === "done" || chunk.type === "error") return;
        } catch {
          // Malformed SSE line — skip
        }
      }
    }
  }
}

// ── Documents ─────────────────────────────────────────────────────────────────

export const documents = {
  upload: (file: File, isPublic = false) => {
    const form = new FormData();
    form.append("file", file);
    form.append("is_public", String(isPublic));
    return apiClient
      .post<Document>("/documents/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  list: (page = 1) =>
    apiClient
      .get<{ documents: Document[]; total: number }>(`/documents/?page=${page}`)
      .then((r) => r.data),

  delete: (id: string) => apiClient.delete(`/documents/${id}`),
};

// ── Feedback ──────────────────────────────────────────────────────────────────

export const feedback = {
  submit: (data: { message_id: string; rating: "thumbs_up" | "thumbs_down"; comment?: string }) =>
    apiClient.post<Feedback>("/feedback/", data).then((r) => r.data),
};

// ── Admin ─────────────────────────────────────────────────────────────────────

export const admin = {
  metrics: () => apiClient.get<AdminMetrics>("/admin/metrics").then((r) => r.data),
  users: (page = 1) => apiClient.get(`/admin/users?page=${page}`).then((r) => r.data),
  conversations: (page = 1) => apiClient.get(`/admin/conversations?page=${page}`).then((r) => r.data),
  modelPerformance: () => apiClient.get("/admin/model-performance").then((r) => r.data),
  pendingFeedback: (page = 1) => apiClient.get(`/feedback/pending?page=${page}`).then((r) => r.data),
  reviewFeedback: (id: string, status: string, notes?: string) =>
    apiClient.patch(`/feedback/${id}/review`, { status, review_notes: notes }).then((r) => r.data),
};
