"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Users, MessageSquare, FileText, DollarSign,
  ThumbsUp, ThumbsDown, CheckCircle, XCircle, Clock, ArrowLeft,
} from "lucide-react";
import toast from "react-hot-toast";
import { admin as adminApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import type { AdminMetrics } from "@/types";

function MetricCard({ title, value, sub, icon: Icon, color }: any) {
  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500">{title}</p>
          <p className={`mt-1 text-3xl font-bold ${color || "text-white"}`}>{value}</p>
          {sub && <p className="mt-0.5 text-xs text-gray-500">{sub}</p>}
        </div>
        <div className={`rounded-xl p-3 ${color ? color.replace("text-", "bg-").replace("400", "900/30") : "bg-gray-800"}`}>
          <Icon className={`h-6 w-6 ${color || "text-gray-400"}`} />
        </div>
      </div>
    </div>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [modelPerf, setModelPerf] = useState<any[]>([]);
  const [pendingFeedback, setPendingFeedback] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== "admin" && user?.role !== "moderator") {
      router.replace("/chat");
      return;
    }

    Promise.all([
      adminApi.metrics(),
      adminApi.modelPerformance(),
      adminApi.pendingFeedback(),
    ])
      .then(([m, mp, pf]) => {
        setMetrics(m);
        setModelPerf(mp);
        setPendingFeedback(pf);
      })
      .catch(() => toast.error("Failed to load metrics"))
      .finally(() => setLoading(false));
  }, [user, router]);

  const handleReview = async (id: string, status: "approved" | "rejected") => {
    try {
      await adminApi.reviewFeedback(id, status);
      setPendingFeedback((prev) => prev.filter((f) => f.id !== id));
      toast.success(`Feedback ${status}`);
    } catch {
      toast.error("Review failed");
    }
  };

  if (loading || !metrics) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8 flex items-center gap-4">
          <button
            onClick={() => router.push("/chat")}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-800 hover:text-white"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
            <p className="text-sm text-gray-400">Monitor usage, feedback, and model performance</p>
          </div>
        </div>

        {/* Key metrics */}
        <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard
            title="Total Users"
            value={metrics.users.total.toLocaleString()}
            sub={`${metrics.users.active} active`}
            icon={Users}
            color="text-blue-400"
          />
          <MetricCard
            title="Conversations"
            value={metrics.conversations.total.toLocaleString()}
            sub={`${metrics.conversations.total_messages} messages`}
            icon={MessageSquare}
            color="text-purple-400"
          />
          <MetricCard
            title="Documents"
            value={metrics.documents.total.toLocaleString()}
            icon={FileText}
            color="text-yellow-400"
          />
          <MetricCard
            title="AI Cost"
            value={`$${metrics.ai_usage.total_cost_usd.toFixed(2)}`}
            sub={`${(metrics.ai_usage.total_tokens / 1000).toFixed(1)}K tokens`}
            icon={DollarSign}
            color="text-green-400"
          />
        </div>

        {/* Feedback + Model perf */}
        <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Feedback stats */}
          <div className="rounded-2xl border border-gray-800 bg-gray-900 p-6">
            <h2 className="mb-4 font-semibold text-white">User Satisfaction</h2>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-xl bg-green-900/20 p-3 text-center">
                <ThumbsUp className="mx-auto mb-1 h-5 w-5 text-green-400" />
                <p className="text-xl font-bold text-green-400">{metrics.feedback.positive}</p>
                <p className="text-xs text-gray-500">Positive</p>
              </div>
              <div className="rounded-xl bg-red-900/20 p-3 text-center">
                <ThumbsDown className="mx-auto mb-1 h-5 w-5 text-red-400" />
                <p className="text-xl font-bold text-red-400">{metrics.feedback.total - metrics.feedback.positive}</p>
                <p className="text-xs text-gray-500">Negative</p>
              </div>
              <div className="rounded-xl bg-brand-900/20 p-3 text-center">
                <p className="text-xl font-bold text-brand-400">{metrics.feedback.satisfaction_rate}%</p>
                <p className="text-xs text-gray-500">Satisfaction</p>
              </div>
            </div>
          </div>

          {/* Model performance chart */}
          <div className="rounded-2xl border border-gray-800 bg-gray-900 p-6">
            <h2 className="mb-4 font-semibold text-white">Avg Latency by Model (ms)</h2>
            {modelPerf.length > 0 ? (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={modelPerf}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="model" tick={{ fontSize: 11, fill: "#9ca3af" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151" }}
                    labelStyle={{ color: "#f9fafb" }}
                  />
                  <Bar dataKey="avg_latency_ms" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-8 text-center text-sm text-gray-500">No data yet</p>
            )}
          </div>
        </div>

        {/* Pending feedback review (RLHF queue) */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-white">Pending Feedback Review (RLHF Queue)</h2>
            <span className="rounded-full bg-yellow-900/30 px-2.5 py-0.5 text-xs font-medium text-yellow-400">
              {pendingFeedback.length} items
            </span>
          </div>

          {pendingFeedback.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500">All caught up! No pending reviews.</p>
          ) : (
            <div className="space-y-3">
              {pendingFeedback.map((fb) => (
                <div
                  key={fb.id}
                  className="rounded-xl border border-gray-700 bg-gray-800/60 p-4"
                >
                  <div className="mb-2 flex items-center gap-2">
                    {fb.rating === "thumbs_up" ? (
                      <ThumbsUp className="h-4 w-4 text-green-400" />
                    ) : (
                      <ThumbsDown className="h-4 w-4 text-red-400" />
                    )}
                    <span className="text-xs text-gray-400">{new Date(fb.created_at).toLocaleString()}</span>
                  </div>
                  {fb.comment && (
                    <p className="mb-2 text-sm text-gray-300 italic">&quot;{fb.comment}&quot;</p>
                  )}
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleReview(fb.id, "approved")}
                      className="flex items-center gap-1 rounded-lg bg-green-900/30 px-3 py-1.5 text-xs font-medium text-green-400 transition hover:bg-green-900/50"
                    >
                      <CheckCircle className="h-3.5 w-3.5" />
                      Approve for Training
                    </button>
                    <button
                      onClick={() => handleReview(fb.id, "rejected")}
                      className="flex items-center gap-1 rounded-lg bg-red-900/30 px-3 py-1.5 text-xs font-medium text-red-400 transition hover:bg-red-900/50"
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
