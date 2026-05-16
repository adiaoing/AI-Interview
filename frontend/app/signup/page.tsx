"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const supabase = createClient();
    if (!supabase) { setError("Auth not configured."); setLoading(false); return; }
    const { error } = await supabase.auth.signUp({ email, password, options: { emailRedirectTo: `${location.origin}/interview/setup` } });
    if (error) { setError(error.message); setLoading(false); }
    else { setSuccess(true); }
  }

  if (success) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center px-6 cursor-pointer" onClick={() => router.back()}>
        <div className="fixed inset-0 pointer-events-none" style={{ background: "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(10,132,255,0.07) 0%, transparent 60%)" }} />
        <div className="relative w-full max-w-sm text-center animate-scale-in cursor-default" onClick={(e) => e.stopPropagation()}>
          <div className="w-16 h-16 rounded-2xl mx-auto mb-6 flex items-center justify-center" style={{ background: "rgba(48,209,88,0.1)", border: "1px solid rgba(48,209,88,0.2)" }}>
            <span className="text-2xl">✓</span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-3">Check your email</h1>
          <p className="text-[14px] leading-relaxed" style={{ color: "rgba(245,245,247,0.45)" }}>
            We sent a confirmation link to <span className="text-white/70">{email}</span>. Click it to activate your account.
          </p>
          <Link href="/login" className="inline-block mt-8 text-[13px] font-medium" style={{ color: "#0A84FF" }}>Back to sign in</Link>
        </div>
      </div>
    );
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
          <h1 className="text-2xl font-bold text-white tracking-tight">Create your account</h1>
          <p className="text-[14px] mt-1.5" style={{ color: "rgba(245,245,247,0.45)" }}>Start practicing with your AI coach</p>
        </div>

        <div className="rounded-2xl px-7 py-8 space-y-5" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <form onSubmit={handleSignup} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[13px] font-medium block" style={{ color: "rgba(255,255,255,0.55)" }} htmlFor="email">Email</label>
              <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="you@example.com" className="input-apple w-full rounded-xl px-4 py-2.5 text-[14px]" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[13px] font-medium block" style={{ color: "rgba(255,255,255,0.55)" }} htmlFor="password">Password</label>
              <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} placeholder="Min. 8 characters" className="input-apple w-full rounded-xl px-4 py-2.5 text-[14px]" />
            </div>
            {error && <p className="text-[13px] rounded-xl px-3 py-2.5" style={{ color: "#FF6B6B", background: "rgba(255,107,107,0.08)", border: "1px solid rgba(255,107,107,0.15)" }}>{error}</p>}
            <button type="submit" disabled={loading} className="w-full py-2.5 rounded-xl text-[14px] font-semibold text-white transition-all duration-200 disabled:opacity-50 active:scale-[0.98] mt-1" style={{ background: "#0A84FF", boxShadow: "0 0 0 1px rgba(10,132,255,0.3), 0 4px 16px rgba(10,132,255,0.25)" }}>
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>
        </div>

        <p className="text-center text-[13px] mt-6" style={{ color: "rgba(255,255,255,0.3)" }}>
          Already have an account?{" "}
          <Link href="/login" className="font-medium" style={{ color: "#0A84FF" }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}
