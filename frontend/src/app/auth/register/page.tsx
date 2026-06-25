"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { auth } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Bot, Loader2 } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [form, setForm] = useState({ email: "", username: "", password: "", full_name: "" });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await auth.register(form);
      setAuth(data.user, data.access_token, data.refresh_token);
      toast.success("Account created! Welcome.");
      router.push("/chat");
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      toast.error(Array.isArray(detail) ? detail[0]?.msg : (detail ?? "Registration failed"));
    } finally {
      setLoading(false);
    }
  };

  const field = (key: keyof typeof form, label: string, type = "text", placeholder = "") => (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-gray-300">{label}</label>
      <input
        type={type}
        required={key !== "full_name"}
        value={form[key]}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-white placeholder-gray-500 outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        placeholder={placeholder}
      />
    </div>
  );

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600">
            <Bot className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Create your account</h1>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-gray-800 bg-gray-900 p-8 shadow-2xl"
        >
          <div className="space-y-5">
            {field("full_name", "Full Name (optional)", "text", "Jane Doe")}
            {field("username", "Username", "text", "janedoe")}
            {field("email", "Email", "email", "you@example.com")}
            {field("password", "Password", "password", "Min 8 chars, 1 uppercase, 1 number")}

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 font-semibold text-white transition hover:bg-brand-500 disabled:opacity-60"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Create Account
            </button>
          </div>
        </form>

        <p className="mt-5 text-center text-sm text-gray-400">
          Already have an account?{" "}
          <Link href="/auth/login" className="text-brand-400 hover:text-brand-300 font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
