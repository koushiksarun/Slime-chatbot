"use client";

import { useEffect, useRef, useState } from "react";
import { useChat } from "@/hooks/useChat";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";
import { DocumentUpload } from "@/components/upload/DocumentUpload";
import { chat as chatApi } from "@/lib/api";
import {
  Bot,
  PanelLeftOpen,
  PanelLeftClose,
  FileText,
  X,
  Search,
  Globe2,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { clsx } from "clsx";
import type { Document } from "@/types";

const EMPTY_STATE_PROMPTS: Array<{ title: string; body: string; prompt: string; Icon: LucideIcon }> = [
  {
    title: "Digest my sources",
    body: "Turn uploaded files into crisp takeaways.",
    prompt: "Summarize my uploaded document and pull out the most important decisions, risks, and next steps.",
    Icon: FileText,
  },
  {
    title: "Research with tools",
    body: "Use agent mode for broader context.",
    prompt: "Research this topic with tools enabled and give me a concise, sourced briefing.",
    Icon: Globe2,
  },
  {
    title: "Shape an idea",
    body: "Brainstorm, compare, debug, or draft.",
    prompt: "Help me turn a rough idea into a practical plan with options and tradeoffs.",
    Icon: Search,
  },
];

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [docsOpen, setDocsOpen] = useState(false);
  const [useRag, setUseRag] = useState(true);
  const [useAgents, setUseAgents] = useState(false);
  const [selectedDocs, setSelectedDocs] = useState<Document[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | undefined>();

  const {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    loadMessages,
  } = useChat({
    conversationId: activeConvId,
    useRag,
    useAgents,
    documentIds: selectedDocs.filter((d) => d.status === "ready").map((d) => d.id),
    onConversationCreated: (id) => setActiveConvId(id),
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const handleSelectConversation = async (id: string) => {
    try {
      const conv = await chatApi.getConversation(id);
      setActiveConvId(id);
      loadMessages(conv.messages ?? [], id);
    } catch {}
  };

  const handleNewChat = () => {
    clearMessages();
    setActiveConvId(undefined);
  };

  const firstMessage = messages[0]?.content;
  const readyDocs = selectedDocs.filter((doc) => doc.status === "ready").length;

  return (
    <div className="flex h-screen overflow-hidden bg-app text-gray-100">
      {sidebarOpen && (
        <ChatSidebar
          currentConversationId={activeConvId}
          onSelectConversation={handleSelectConversation}
          onNewChat={handleNewChat}
        />
      )}

      <div className="relative flex flex-1 flex-col overflow-hidden">
        <div className="pointer-events-none absolute inset-0 slime-flow animate-shimmer opacity-55" />
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(2,8,6,0.54),rgba(3,7,18,0.98)),repeating-linear-gradient(90deg,rgba(255,255,255,0.022)_0_1px,transparent_1px_96px),repeating-linear-gradient(0deg,rgba(255,255,255,0.018)_0_1px,transparent_1px_96px)]" />

        <header className="relative z-10 flex h-16 items-center gap-3 border-b border-white/10 bg-gray-950/55 px-4 backdrop-blur-2xl">
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="rounded-lg border border-white/10 bg-white/[0.035] p-2 text-gray-400 transition hover:border-brand-300/30 hover:bg-white/10 hover:text-white focus:outline-none focus:ring-2 focus:ring-brand-300/30"
            aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          >
            {sidebarOpen ? <PanelLeftClose className="h-5 w-5" /> : <PanelLeftOpen className="h-5 w-5" />}
          </button>

          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="slime-mark flex h-10 w-10 shrink-0 items-center justify-center">
              <Bot className="h-[18px] w-[18px] text-gray-950" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="truncate text-sm font-semibold text-white">
                  {firstMessage ? `${firstMessage.slice(0, 64)}${firstMessage.length > 64 ? "..." : ""}` : "SLIME AI"}
                </p>
                <span className="hidden rounded-full border border-brand-300/25 bg-brand-400/10 px-2 py-0.5 text-[11px] font-semibold text-brand-100 sm:inline-flex">
                  online
                </span>
              </div>
              <p className="hidden text-xs text-gray-400 sm:block">
                {useRag ? "Retrieval on" : "General chat"} - {useAgents ? "agent tools on" : "agent tools off"} - {readyDocs} ready docs
              </p>
            </div>
          </div>

          <button
            onClick={() => setDocsOpen((v) => !v)}
            className={clsx(
              "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-semibold transition focus:outline-none focus:ring-2 focus:ring-brand-300/30",
              docsOpen || selectedDocs.length > 0
                ? "border-brand-300/40 bg-brand-500/15 text-brand-100 shadow-glow"
                : "border-white/10 bg-white/[0.055] text-gray-300 hover:bg-white/10 hover:text-white"
            )}
          >
            <FileText className="h-4 w-4" />
            Documents {selectedDocs.length > 0 && `(${selectedDocs.length})`}
          </button>
        </header>

        <div className="relative z-10 flex flex-1 overflow-hidden">
          <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
            <div className="mx-auto max-w-4xl space-y-5">
              {messages.length === 0 && (
                <div className="flex min-h-full items-start justify-center py-3 lg:min-h-[66vh] lg:items-center lg:py-0">
                  <div className="w-full max-w-3xl">
                    <div className="slime-surface rounded-2xl p-6 text-center sm:p-8">
                      <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center slime-mark sm:h-20 sm:w-20">
                        <Bot className="h-9 w-9 text-gray-950 sm:h-10 sm:w-10" />
                      </div>
                      <h1 className="text-3xl font-semibold text-white sm:text-5xl">
                        SLIME AI
                      </h1>
                      <div className="mt-7 grid gap-3 sm:grid-cols-3">
                        {EMPTY_STATE_PROMPTS.map(({ title, body, prompt, Icon }) => (
                          <button
                            key={title}
                            onClick={() => sendMessage(prompt)}
                            className="group rounded-xl border border-white/10 bg-gray-950/45 p-4 text-left transition duration-300 hover:-translate-y-0.5 hover:border-brand-300/45 hover:bg-white/[0.075] hover:shadow-slime focus:outline-none focus:ring-2 focus:ring-brand-300/30"
                          >
                            <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg border border-brand-300/25 bg-brand-400/10 transition group-hover:border-brand-300/50 group-hover:bg-brand-400/15">
                              <Icon className="h-5 w-5 text-brand-200" />
                            </div>
                            <p className="text-sm font-semibold text-gray-100">{title}</p>
                            <p className="mt-1 text-xs leading-5 text-gray-400">{body}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}

              {isLoading && (
                <div className="ml-12 inline-flex items-center gap-2 rounded-lg border border-brand-300/20 bg-brand-500/10 px-3 py-1 text-xs text-brand-100">
                  <Zap className="h-3.5 w-3.5" />
                  SLIME AI is thinking
                </div>
              )}

              {error && (
                <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200 shadow-soft">
                  {error}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </main>

          {docsOpen && (
            <aside className="w-80 shrink-0 overflow-y-auto border-l border-white/10 bg-gray-950/55 p-4 backdrop-blur-2xl">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-100">Knowledge Dock</h3>
                  <p className="text-xs text-gray-500">Upload files for retrieval.</p>
                </div>
                <button
                  onClick={() => setDocsOpen(false)}
                  className="rounded-xl p-1.5 text-gray-500 transition hover:bg-white/10 hover:text-gray-200"
                  aria-label="Close documents panel"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <DocumentUpload
                existingDocs={selectedDocs}
                onDocumentUploaded={(doc) => setSelectedDocs((prev) => [...prev, doc])}
              />
            </aside>
          )}
        </div>

        <ChatInput
          onSend={sendMessage}
          isLoading={isLoading}
          useRag={useRag}
          useAgents={useAgents}
          onToggleRag={() => setUseRag((v) => !v)}
          onToggleAgents={() => setUseAgents((v) => !v)}
        />
      </div>
    </div>
  );
}
