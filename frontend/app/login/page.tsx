"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/interview/setup";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const supabase = createClient();
    if (!supabase) { setError("Auth not configured."); setLoading(false); return; }
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) { setError(error.message); setLoading(false); }
    else { router.push(next); }
  }

  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-6 cursor-pointer" onClick={() => router.back()}>
      <div className="fixed inset-0 pointer-events-none" style={{ background: "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(10,132,255,0.07) 0%, transparent 60%)" }} />
      <div className="relative w-full max-w-sm animate-scale-in cursor-default" onClick={(e) => e.stopPropagation()}>
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2.5 mb-6">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, #0A84FF, #5E5CE6)", boxShadow: "0 4px 16px rgba(10,132,255,0.3)" }}>
              <span className="text-white text-[11px] font-bold tracking-tight">AI</span>
            </div>
            <span className="text-white font-semibold text-lg">AI Interview</span>
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">Welcome back</h1>
          <p className="text-[14px] mt-1.5" style={{ color: "rgba(245,245,247,0.45)" }}>Sign in to continue your practice</p>
        </div>

        <div className="rounded-2xl px-7 py-8 space-y-5" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[13px] font-medium block" style={{ color: "rgba(255,255,255,0.55)" }} htmlFor="email">Email</label>
              <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="you@example.com" className="input-apple w-full rounded-xl px-4 py-2.5 text-[14px]" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[13px] font-medium block" style={{ color: "rgba(255,255,255,0.55)" }} htmlFor="password">Password</label>
              <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="••••••••" className="input-apple w-full rounded-xl px-4 py-2.5 text-[14px]" />
            </div>
            {error && <p className="text-[13px] rounded-xl px-3 py-2.5" style={{ color: "#FF6B6B", background: "rgba(255,107,107,0.08)", border: "1px solid rgba(255,107,107,0.15)" }}>{error}</p>}
            <button type="submit" disabled={loading} className="w-full py-2.5 rounded-xl text-[14px] font-semibold text-white transition-all duration-200 disabled:opacity-50 active:scale-[0.98] mt-1" style={{ background: "#0A84FF", boxShadow: "0 0 0 1px rgba(10,132,255,0.3), 0 4px 16px rgba(10,132,255,0.25)" }}>
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>

        <p className="text-center text-[13px] mt-6" style={{ color: "rgba(255,255,255,0.3)" }}>
          No account?{" "}
          <Link href="/signup" className="font-medium" style={{ color: "#0A84FF" }}>Sign up free</Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return <Suspense><LoginForm /></Suspense>;
}
