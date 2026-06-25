"use client";

import { useState, useCallback, useRef } from "react";
import { streamChat } from "@/lib/api";
import type { Message, Citation, Conversation } from "@/types";
import { nanoid } from "nanoid";

// Lightweight nanoid polyfill if not installed
function uid() {
  return Math.random().toString(36).slice(2, 11);
}

interface UseChatOptions {
  conversationId?: string;
  useRag?: boolean;
  useAgents?: boolean;
  documentIds?: string[];
  onConversationCreated?: (id: string) => void;
}

export function useChat(options: UseChatOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | undefined>(
    options.conversationId
  );
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      setError(null);

      // Add user message optimistically
      const userMessage: Message = {
        id: uid(),
        role: "user",
        content,
        prompt_tokens: 0,
        completion_tokens: 0,
        cost_usd: 0,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Add streaming placeholder for assistant
      const assistantId = uid();
      const assistantPlaceholder: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        prompt_tokens: 0,
        completion_tokens: 0,
        cost_usd: 0,
        created_at: new Date().toISOString(),
        isStreaming: true,
      };
      setMessages((prev) => [...prev, assistantPlaceholder]);
      setIsLoading(true);

      try {
        let finalContent = "";
        let finalCitations: Citation[] = [];
        let finalMessageId = assistantId;

        const generator = streamChat({
          message: content,
          conversation_id: conversationId,
          use_rag: options.useRag ?? true,
          use_agents: options.useAgents ?? false,
          document_ids: options.documentIds,
        });

        for await (const chunk of generator) {
          if (chunk.type === "token" && chunk.content) {
            finalContent += chunk.content;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: finalContent }
                  : m
              )
            );
          } else if (chunk.type === "citation" && chunk.citations) {
            finalCitations = chunk.citations;
          } else if (chunk.type === "done") {
            if (chunk.conversation_id && !conversationId) {
              setConversationId(chunk.conversation_id);
              options.onConversationCreated?.(chunk.conversation_id);
            }
            if (chunk.message_id) finalMessageId = chunk.message_id;
          } else if (chunk.type === "error") {
            throw new Error(chunk.error || "Stream error");
          }
        }

        // Finalize message with server ID and citations
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  id: finalMessageId,
                  citations: finalCitations.length > 0 ? finalCitations : undefined,
                  isStreaming: false,
                }
              : m
          )
        );
      } catch (err: any) {
        setError(err.message ?? "Failed to send message");
        setMessages((prev) => prev.filter((m) => m.id !== assistantId));
      } finally {
        setIsLoading(false);
      }
    },
    [conversationId, isLoading, options]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(undefined);
    setError(null);
  }, []);

  const loadMessages = useCallback((msgs: Message[], convId: string) => {
    setMessages(msgs);
    setConversationId(convId);
  }, []);

  return {
    messages,
    isLoading,
    error,
    conversationId,
    sendMessage,
    clearMessages,
    loadMessages,
  };
}
