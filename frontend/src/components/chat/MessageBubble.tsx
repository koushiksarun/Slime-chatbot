"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { ThumbsUp, ThumbsDown, BookOpen, Bot, User, Wrench } from "lucide-react";
import { clsx } from "clsx";
import type { Message, Citation } from "@/types";
import { feedback as feedbackApi } from "@/lib/api";
import { useState } from "react";
import toast from "react-hot-toast";

interface Props {
  message: Message;
}

function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <button
      onClick={() => setExpanded((v) => !v)}
      className="flex w-full flex-col gap-1 rounded-xl border border-white/10 bg-white/[0.045] p-3 text-left transition hover:border-brand-300/40 hover:bg-white/[0.07] focus:outline-none focus:ring-2 focus:ring-brand-400/20"
    >
      <div className="flex items-center gap-2 text-xs font-semibold text-brand-200">
        <BookOpen className="h-3.5 w-3.5 shrink-0" />
        <span className="min-w-0 flex-1 truncate">Source {index + 1}: {citation.document_name}</span>
        <span className="shrink-0 rounded-full bg-brand-400/10 px-2 py-0.5 text-[11px] text-brand-100">
          {Math.round(citation.score * 100)}%
        </span>
      </div>
      {expanded && (
        <p className="mt-2 text-xs leading-5 text-gray-400">{citation.chunk_text}</p>
      )}
    </button>
  );
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  const [voted, setVoted] = useState<"up" | "down" | null>(null);

  const vote = async (rating: "thumbs_up" | "thumbs_down") => {
    if (voted || message.isStreaming) return;
    try {
      await feedbackApi.submit({ message_id: message.id, rating });
      setVoted(rating === "thumbs_up" ? "up" : "down");
      toast.success("Thanks for your feedback!");
    } catch {
      toast.error("Could not submit feedback");
    }
  };

  return (
    <div className={clsx("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      {/* Avatar */}
      <div
        className={clsx(
          "mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border text-white shadow-soft",
          isUser
            ? "border-brand-300/25 bg-brand-500/20 text-brand-100"
            : "border-white/10 bg-white/[0.06] text-gray-200"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Bubble */}
      <div className={clsx("max-w-[min(82%,760px)] space-y-2", isUser ? "items-end" : "items-start")}>
        <div
          className={clsx(
            "rounded-2xl border px-4 py-3 text-sm leading-relaxed shadow-soft",
            isUser
              ? "rounded-tr-md border-brand-300/25 bg-brand-500/20 text-brand-50"
              : "rounded-tl-md border-white/10 bg-white/[0.055] text-gray-100"
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className={clsx("prose prose-sm prose-invert max-w-none prose-dark", message.isStreaming && "cursor-blink")}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, inline, className, children, ...props }: any) {
                    const match = /language-(\w+)/.exec(className || "");
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        className="!my-3 !rounded-xl !border !border-white/10 !bg-gray-950/70 !text-xs"
                        {...props}
                      >
                        {String(children).replace(/\n$/, "")}
                      </SyntaxHighlighter>
                    ) : (
                      <code className="rounded-md border border-white/10 bg-gray-950/70 px-1.5 py-0.5 text-xs text-brand-100" {...props}>
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="space-y-2">
            {message.citations.map((c, i) => (
              <CitationCard key={i} citation={c} index={i} />
            ))}
          </div>
        )}

        {/* Tool calls */}
        {!isUser && message.tool_calls && message.tool_calls.length > 0 && (
          <div className="space-y-1 rounded-xl border border-amber-300/20 bg-amber-500/10 p-3 text-xs">
            {message.tool_calls.map((tc, i) => (
              <div key={i} className="flex gap-2 text-amber-100">
                <Wrench className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span className="font-mono">{tc.tool}</span>
                <span className="min-w-0 truncate text-gray-500">{tc.output.slice(0, 120)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Feedback buttons */}
        {!isUser && !message.isStreaming && message.content && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => vote("thumbs_up")}
              className={clsx(
                "rounded-lg p-1.5 transition hover:bg-white/10",
                voted === "up" ? "text-green-400" : "text-gray-500 hover:text-gray-300"
              )}
              aria-label="Good response"
            >
              <ThumbsUp className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => vote("thumbs_down")}
              className={clsx(
                "rounded-lg p-1.5 transition hover:bg-white/10",
                voted === "down" ? "text-red-400" : "text-gray-500 hover:text-gray-300"
              )}
              aria-label="Bad response"
            >
              <ThumbsDown className="h-3.5 w-3.5" />
            </button>
            {message.model_used && (
              <span className="ml-2 self-center rounded-full border border-white/10 bg-white/[0.035] px-2 py-0.5 text-[11px] text-gray-500">{message.model_used}</span>
            )}
            {message.latency_ms && (
              <span className="self-center text-[11px] text-gray-600">{message.latency_ms}ms</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
