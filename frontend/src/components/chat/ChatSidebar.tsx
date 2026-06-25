"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clsx } from "clsx";
import { Plus, MessageSquare, Trash2, Bot, LogOut, Shield, Sparkles } from "lucide-react";
import toast from "react-hot-toast";
import { chat as chatApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import type { Conversation } from "@/types";
import { formatDistanceToNow } from "date-fns";

interface Props {
  currentConversationId?: string;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
}

export function ChatSidebar({ currentConversationId, onSelectConversation, onNewChat }: Props) {
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();
  const [conversations, setConversations] = useState<Conversation[]>([]);

  useEffect(() => {
    chatApi.listConversations().then(setConversations).catch(() => {});
  }, [currentConversationId]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await chatApi.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (id === currentConversationId) onNewChat();
      toast.success("Conversation deleted");
    } catch {
      toast.error("Failed to delete");
    }
  };

  const handleLogout = () => {
    clearAuth();
    router.push("/auth/login");
  };

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-white/10 bg-gray-950/95 shadow-soft backdrop-blur-xl">
      {/* Header */}
      <div className="border-b border-white/10 px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-brand-300/25 bg-brand-400/10">
            <Bot className="h-5 w-5 text-brand-200" />
          </div>
          <div className="min-w-0">
            <p className="truncate font-semibold tracking-tight text-white">Slime</p>
            <p className="flex items-center gap-1.5 text-xs text-gray-500">
              <Sparkles className="h-3 w-3 text-brand-300" />
              Gen AI assistant
            </p>
          </div>
        </div>
      </div>

      {/* New Chat button */}
      <div className="px-3 py-3">
        <button
          onClick={onNewChat}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-brand-300/25 bg-brand-500/15 px-3 py-2.5 text-sm font-semibold text-brand-100 transition hover:border-brand-300/50 hover:bg-brand-500/25 focus:outline-none focus:ring-2 focus:ring-brand-400/40"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </button>
      </div>

      {/* Conversation list */}
      <nav className="flex-1 overflow-y-auto px-2 pb-2">
        {conversations.length === 0 ? (
          <div className="mx-2 rounded-xl border border-white/10 bg-white/[0.035] px-3 py-6 text-center">
            <MessageSquare className="mx-auto mb-2 h-5 w-5 text-gray-600" />
            <p className="text-xs font-medium text-gray-400">No conversations yet</p>
            <p className="mt-1 text-xs leading-5 text-gray-600">Start a chat and it will appear here.</p>
          </div>
        ) : (
          <ul className="space-y-1">
            {conversations.map((conv) => (
              <li key={conv.id}>
                <button
                  onClick={() => onSelectConversation(conv.id)}
                  className={clsx(
                    "group flex w-full items-start gap-3 rounded-xl border px-3 py-2.5 text-left text-sm transition focus:outline-none focus:ring-2 focus:ring-brand-400/30",
                    conv.id === currentConversationId
                      ? "border-brand-300/25 bg-brand-500/15 text-white"
                      : "border-transparent text-gray-400 hover:border-white/10 hover:bg-white/[0.055] hover:text-gray-200"
                  )}
                >
                  <MessageSquare className={clsx("mt-0.5 h-4 w-4 shrink-0", conv.id === currentConversationId ? "text-brand-300" : "text-gray-600")} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium leading-tight">
                      {conv.title || "New conversation"}
                    </p>
                    <p className="mt-1 text-xs text-gray-600">
                      {formatDistanceToNow(new Date(conv.updated_at), { addSuffix: true })}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, conv.id)}
                    className="invisible shrink-0 rounded-lg p-1.5 text-gray-600 transition hover:bg-red-500/10 hover:text-red-300 group-hover:visible"
                    aria-label="Delete conversation"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </button>
              </li>
            ))}
          </ul>
        )}
      </nav>

      {/* User section */}
      <div className="space-y-1 border-t border-white/10 p-3">
        {user?.role === "admin" && (
          <button
            onClick={() => router.push("/admin")}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-gray-400 transition hover:bg-white/[0.055] hover:text-gray-200"
          >
            <Shield className="h-4 w-4" />
            Admin Dashboard
          </button>
        )}
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-gray-400 transition hover:bg-red-500/10 hover:text-red-300"
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </button>
        <div className="mt-2 rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2">
          <p className="text-xs font-medium text-gray-300">{user?.full_name || user?.username}</p>
          <p className="truncate text-xs text-gray-500">{user?.email}</p>
        </div>
      </div>
    </aside>
  );
}
