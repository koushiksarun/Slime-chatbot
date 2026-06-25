"use client";

import { useState, useRef, useCallback } from "react";
import { Send, StopCircle, Globe, Paperclip, CornerDownLeft } from "lucide-react";
import { clsx } from "clsx";

interface Props {
  onSend: (message: string) => void;
  isLoading: boolean;
  onStop?: () => void;
  useRag: boolean;
  useAgents: boolean;
  onToggleRag: () => void;
  onToggleAgents: () => void;
}

export function ChatInput({
  onSend, isLoading, onStop, useRag, useAgents, onToggleRag, onToggleAgents
}: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault();
      const trimmed = value.trim();
      if (!trimmed || isLoading) return;
      onSend(trimmed);
      setValue("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    },
    [value, isLoading, onSend]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  return (
    <div className="relative z-10 border-t border-white/10 bg-gray-950/80 px-4 py-4 backdrop-blur-xl">
      <div className="mx-auto max-w-4xl">
      {/* Toggle pills */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <button
          onClick={onToggleRag}
          className={clsx(
            "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition focus:outline-none focus:ring-2 focus:ring-brand-400/30",
            useRag
              ? "border-brand-300/35 bg-brand-500/15 text-brand-100"
              : "border-white/10 bg-white/[0.035] text-gray-400 hover:bg-white/[0.07] hover:text-gray-200"
          )}
        >
          <Paperclip className="h-3.5 w-3.5" />
          Document Search
        </button>
        <button
          onClick={onToggleAgents}
          className={clsx(
            "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition focus:outline-none focus:ring-2 focus:ring-amber-400/30",
            useAgents
              ? "border-amber-300/35 bg-amber-500/15 text-amber-100"
              : "border-white/10 bg-white/[0.035] text-gray-400 hover:bg-white/[0.07] hover:text-gray-200"
          )}
        >
          <Globe className="h-3.5 w-3.5" />
          Web + Tools
        </button>
        <span className="ml-auto hidden items-center gap-1.5 text-xs text-gray-600 sm:flex">
          <CornerDownLeft className="h-3.5 w-3.5" />
          Enter to send
        </span>
      </div>

      <form onSubmit={handleSubmit} className="flex items-end gap-3 rounded-2xl border border-white/10 bg-white/[0.045] p-2 shadow-soft transition focus-within:border-brand-300/40 focus-within:ring-2 focus-within:ring-brand-400/10">
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Send a message… (Shift+Enter for newline)"
            className="max-h-[200px] min-h-11 w-full resize-none rounded-xl border border-transparent bg-transparent px-3 py-3 text-sm leading-6 text-white placeholder-gray-500 outline-none disabled:opacity-50"
            disabled={isLoading}
          />
        </div>

        {isLoading ? (
          <button
            type="button"
            onClick={onStop}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-red-300/25 bg-red-500/15 text-red-200 transition hover:bg-red-500/25 focus:outline-none focus:ring-2 focus:ring-red-400/30"
            aria-label="Stop response"
          >
            <StopCircle className="h-5 w-5" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!value.trim()}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-500 text-white shadow-glow transition hover:bg-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-300/50 disabled:cursor-not-allowed disabled:bg-gray-700 disabled:text-gray-500 disabled:shadow-none"
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </button>
        )}
      </form>

      <p className="mt-2 text-center text-xs text-gray-600">
        AI can make mistakes. Verify important information.
      </p>
      </div>
    </div>
  );
}
