"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { useChat } from "@/hooks/useChat";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";
import { DocumentUpload } from "@/components/upload/DocumentUpload";
import { chat as chatApi } from "@/lib/api";
import { Bot, PanelLeftOpen, PanelLeftClose, FileText, X, Sparkles, Search, Globe2, type LucideIcon } from "lucide-react";
import { clsx } from "clsx";
import type { Document } from "@/types";

const EMPTY_STATE_PROMPTS: Array<{ title: string; body: string; Icon: LucideIcon }> = [
  { title: "Summarize a document", body: "Upload a PDF and ask for key points.", Icon: FileText },
  { title: "Research a topic", body: "Use web tools for current context.", Icon: Globe2 },
  { title: "Ask anything", body: "Brainstorm, write, debug, compare.", Icon: Search },
];

export default function ChatPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
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
    conversationId,
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
    if (!isAuthenticated) router.replace("/auth/login");
  }, [isAuthenticated, router]);

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

  if (!isAuthenticated) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-app text-gray-100">
      {/* Sidebar */}
      {sidebarOpen && (
        <ChatSidebar
          currentConversationId={activeConvId}
          onSelectConversation={handleSelectConversation}
          onNewChat={handleNewChat}
        />
      )}

      {/* Main chat area */}
      <div className="relative flex flex-1 flex-col overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_45%_-20%,rgba(14,165,233,0.12),transparent_32%),linear-gradient(180deg,rgba(15,23,42,0.78),rgba(3,7,18,0.96))]" />
        {/* Top bar */}
        <header className="relative z-10 flex h-16 items-center gap-3 border-b border-white/10 bg-gray-950/70 px-4 backdrop-blur-xl">
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="rounded-lg p-2 text-gray-400 transition hover:bg-white/10 hover:text-white"
            aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          >
            {sidebarOpen ? <PanelLeftClose className="h-5 w-5" /> : <PanelLeftOpen className="h-5 w-5" />}
          </button>

          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-gray-100">
              {messages.length > 0 ? (messages[0]?.content?.slice(0, 64) + "…") : "New Chat"}
            </p>
            <p className="hidden text-xs text-gray-500 sm:block">
              {useRag ? "Document retrieval on" : "General chat"} · {useAgents ? "Agent tools on" : "Agent tools off"}
            </p>
          </div>

          <button
            onClick={() => setDocsOpen((v) => !v)}
            className={clsx(
              "flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold transition",
              docsOpen || selectedDocs.length > 0
                ? "border-brand-400/40 bg-brand-500/15 text-brand-200"
                : "border-white/10 bg-white/[0.04] text-gray-300 hover:bg-white/10 hover:text-white"
            )}
          >
            <FileText className="h-4 w-4" />
            Documents {selectedDocs.length > 0 && `(${selectedDocs.length})`}
          </button>
        </header>

        <div className="relative z-10 flex flex-1 overflow-hidden">
          {/* Messages */}
          <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
            <div className="mx-auto max-w-4xl space-y-6">
              {messages.length === 0 && (
                <div className="flex min-h-full items-start justify-center py-3 lg:min-h-[66vh] lg:items-center lg:py-0">
                  <div className="w-full max-w-3xl">
                    <div className="mb-5 text-center sm:mb-8">
                      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-brand-300/25 bg-brand-400/10 shadow-glow sm:h-16 sm:w-16">
                        <Bot className="h-7 w-7 text-brand-200 sm:h-8 sm:w-8" />
                      </div>
                      <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-medium text-gray-300">
                        <Sparkles className="h-3.5 w-3.5 text-brand-300" />
                        RAG, memory, and agent tools ready
                      </div>
                      <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:mt-4 sm:text-4xl">
                        What are we building today?
                      </h2>
                      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-gray-400">
                        Ask a question, upload source files, or let the agent use tools when the answer needs extra context.
                      </p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-3">
                      {EMPTY_STATE_PROMPTS.map(({ title, body, Icon }) => (
                        <button
                          key={title}
                          onClick={() => sendMessage(title)}
                          className="group rounded-2xl border border-white/10 bg-white/[0.045] p-4 text-left transition hover:border-brand-300/40 hover:bg-white/[0.075]"
                        >
                          <Icon className="mb-3 h-5 w-5 text-brand-300 transition group-hover:text-brand-200" />
                          <p className="text-sm font-semibold text-gray-100">{title}</p>
                          <p className="mt-1 text-xs leading-5 text-gray-500">{body}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}

              {error && (
                <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200 shadow-soft">
                  {error}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </main>

          {/* Document panel */}
          {docsOpen && (
            <aside className="w-80 shrink-0 overflow-y-auto border-l border-white/10 bg-gray-950/80 p-4 backdrop-blur-xl">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-100">Documents</h3>
                  <p className="text-xs text-gray-500">Upload files for retrieval.</p>
                </div>
                <button
                  onClick={() => setDocsOpen(false)}
                  className="rounded-lg p-1.5 text-gray-500 transition hover:bg-white/10 hover:text-gray-200"
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

        {/* Input */}
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
