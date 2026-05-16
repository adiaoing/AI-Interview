import Link from "next/link";

export default function CTA() {
  return (
    <section className="py-28 px-6 relative overflow-hidden">
      {/* Glow behind */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse 60% 70% at 50% 50%, rgba(10,132,255,0.07) 0%, rgba(94,92,230,0.04) 40%, transparent 70%)",
        }}
      />

      {/* Border card */}
      <div
        className="relative max-w-3xl mx-auto rounded-3xl px-10 py-16 text-center"
        style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.08)",
          boxShadow: "0 0 60px rgba(10,132,255,0.06), inset 0 1px 0 rgba(255,255,255,0.06)",
        }}
      >
        {/* Top accent line */}
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 h-px w-1/2 rounded-full"
          style={{ background: "linear-gradient(90deg, transparent, rgba(10,132,255,0.4), transparent)" }}
        />

        <p
          className="text-[13px] font-medium mb-5 tracking-widest uppercase"
          style={{ color: "#0A84FF", letterSpacing: "0.08em" }}
        >
          Start today — it&apos;s free
        </p>

        <h2
          className="text-[clamp(1.8rem,4vw,2.8rem)] font-bold leading-tight tracking-tight mb-5"
          style={{
            background: "linear-gradient(180deg, #ffffff 0%, rgba(255,255,255,0.7) 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          Your dream job is one practice session away
        </h2>

        <p className="text-base leading-relaxed mb-10 max-w-xl mx-auto" style={{ color: "rgba(245,245,247,0.42)" }}>
          Stop memorizing answers. Start building real interview instincts with an AI that
          pushes you, coaches you, and adapts to your level every single turn.
        </p>

        <Link
          href="/signup"
          className="inline-block text-[15px] font-semibold px-10 py-3.5 rounded-full text-white transition-all duration-200 active:scale-95"
          style={{
            background: "#0A84FF",
            boxShadow: "0 0 0 1px rgba(10,132,255,0.3), 0 4px 24px rgba(10,132,255,0.35)",
          }}
        >
          Start your first interview — it&apos;s free
        </Link>

        <p className="mt-5 text-[12px]" style={{ color: "rgba(255,255,255,0.2)" }}>
          No credit card · No setup · Instant access
        </p>
      </div>
    </section>
  );
}
