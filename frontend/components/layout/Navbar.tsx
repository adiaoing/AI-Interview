"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";
import type { User } from "@supabase/supabase-js";

export default function Navbar() {
  const [user, setUser] = useState<User | null>(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    if (supabase) {
      supabase.auth.getUser().then(({ data }) => setUser(data.user));
      const { data: { subscription } } = supabase.auth.onAuthStateChange((_, session) => {
        setUser(session?.user ?? null);
      });
      return () => subscription.unsubscribe();
    }
  }, []);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 16);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  async function handleSignOut() {
    const supabase = createClient();
    if (supabase) await supabase.auth.signOut();
    window.location.href = "/";
  }

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-black/75 backdrop-blur-2xl border-b border-white/[0.06]"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 flex items-center justify-between" style={{ height: "60px" }}>
        <Link href="/" className="flex items-center gap-2.5 group">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center shadow-lg"
            style={{
              background: "linear-gradient(135deg, #0A84FF, #5E5CE6)",
              boxShadow: "0 4px 12px rgba(10,132,255,0.3)",
            }}
          >
            <span className="text-white text-[10px] font-bold leading-none tracking-tight">AI</span>
          </div>
          <span
            className="text-white/90 group-hover:text-white transition-colors"
            style={{ fontFamily: "var(--font-brand)", fontSize: "18px", fontWeight: 800, letterSpacing: "-0.03em" }}
          >
            AI Interview
          </span>
        </Link>

        <div className="flex items-center gap-1.5">
          {user ? (
            <>
              <Link
                href="/interview/setup"
                className="text-[13px] font-medium px-4 py-1.5 rounded-full text-white transition-all duration-200"
                style={{ background: "#0A84FF", boxShadow: "0 2px 12px rgba(10,132,255,0.3)" }}
              >
                Start interview
              </Link>
              <button
                onClick={handleSignOut}
                className="text-[13px] font-medium px-3 py-1.5 rounded-full text-white/40 hover:text-white/70 transition-colors"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="text-[13px] font-medium px-3 py-1.5 rounded-full text-white/50 hover:text-white/80 transition-colors"
              >
                Sign in
              </Link>
              <Link
                href="/signup"
                className="text-[13px] font-medium px-4 py-1.5 rounded-full bg-white text-black hover:bg-white/90 transition-all duration-200"
                style={{ boxShadow: "0 2px 12px rgba(255,255,255,0.12)" }}
              >
                Get started
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
