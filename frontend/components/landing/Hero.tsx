import Link from "next/link";

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center px-6 pt-20 pb-16 overflow-hidden">
      {/* Background glow orbs */}
      <div
        className="absolute pointer-events-none"
        style={{
          top: "15%", left: "50%", transform: "translateX(-50%)",
          width: "600px", height: "600px",
          background: "radial-gradient(circle, rgba(10,132,255,0.12) 0%, transparent 65%)",
          filter: "blur(40px)",
          animation: "glow-pulse 4s ease-in-out infinite",
        }}
      />
      <div
        className="absolute pointer-events-none"
        style={{
          top: "30%", left: "30%",
          width: "400px", height: "400px",
          background: "radial-gradient(circle, rgba(94,92,230,0.08) 0%, transparent 70%)",
          filter: "blur(60px)",
          animation: "glow-pulse 5s ease-in-out infinite 1s",
        }}
      />

      <div className="relative max-w-4xl mx-auto text-center space-y-8">
        {/* Badge */}
        <div className="animate-fade-in inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-[12px] font-medium tracking-wide"
          style={{
            background: "rgba(10,132,255,0.08)",
            border: "1px solid rgba(10,132,255,0.2)",
            color: "rgba(10,132,255,0.9)",
          }}>
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: "#0A84FF",
              boxShadow: "0 0 6px #0A84FF",
              animation: "glow-pulse 2s ease-in-out infinite",
            }}
          />
          AI-Powered · Voice-First · Adaptive
        </div>

        {/* Headline */}
        <div className="animate-fade-up delay-75 space-y-3">
          <h1
            className="text-[clamp(2.8rem,7vw,5.5rem)] font-bold leading-[1.04] tracking-[-0.03em]"
            style={{
              background: "linear-gradient(180deg, #ffffff 0%, rgba(255,255,255,0.72) 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Ace your next interview
            <br />
            <span
              style={{
                background: "linear-gradient(135deg, #0A84FF 0%, #5E5CE6 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              with your AI coach
            </span>
          </h1>
        </div>

        {/* Subtext */}
        <p
          className="animate-fade-up delay-150 text-[clamp(1rem,2vw,1.2rem)] leading-relaxed max-w-2xl mx-auto"
          style={{ color: "rgba(245,245,247,0.52)" }}
        >
          AI Interview listens to your answers, detects knowledge gaps in real time, and adapts
          the difficulty like having a senior engineer run your interview loop.
        </p>

        {/* CTAs */}
        <div className="animate-fade-up delay-300 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/signup"
            className="w-full sm:w-auto text-[15px] font-semibold px-8 py-3 rounded-full text-white transition-all duration-200 active:scale-95"
            style={{
              background: "#0A84FF",
              boxShadow: "0 0 0 1px rgba(10,132,255,0.3), 0 4px 24px rgba(10,132,255,0.35)",
            }}
          >
            Start practicing free
          </Link>
          <Link
            href="#how-it-works"
            className="w-full sm:w-auto text-[15px] font-medium px-8 py-3 rounded-full transition-all duration-200"
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "rgba(245,245,247,0.75)",
            }}
          >
            See how it works
          </Link>
        </div>

        {/* Social proof nudge */}
        <p className="animate-fade-up delay-500 text-[13px]" style={{ color: "rgba(255,255,255,0.22)" }}>
          No credit card required &nbsp;·&nbsp; Behavioral, technical &amp; role-based
        </p>

        {/* Floating preview card */}
        <div
          className="animate-fade-up delay-500 mx-auto mt-4 max-w-sm rounded-2xl p-px"
          style={{
            background: "linear-gradient(135deg, rgba(10,132,255,0.3), rgba(94,92,230,0.3), rgba(10,132,255,0.1))",
          }}
        >
          <div
            className="rounded-2xl px-6 py-4 text-left space-y-3"
            style={{ background: "#0d0d0d" }}
          >
            <div className="flex items-center gap-2">
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold tracking-tight"
                style={{ background: "rgba(10,132,255,0.15)", color: "#0A84FF" }}
              >
                AI
              </div>
              <span className="text-[12px] font-medium" style={{ color: "rgba(255,255,255,0.5)" }}>AI Interview</span>
              <span
                className="ml-auto text-[11px] px-2 py-0.5 rounded-full"
                style={{ background: "rgba(10,132,255,0.1)", color: "#0A84FF" }}
              >
                Senior · 4/5
              </span>
            </div>
            <p className="text-[13px] leading-relaxed" style={{ color: "rgba(255,255,255,0.75)" }}>
              Tell me about a time you had to make a critical architectural decision with incomplete information. How did you approach it?
            </p>
            <div
              className="flex items-center gap-2 text-[12px] rounded-xl px-4 py-2.5"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.07)",
                color: "rgba(255,255,255,0.35)",
              }}
            >
              <span className="w-2 h-2 rounded-full bg-[#0A84FF] animate-pulse" />
              Listening...
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
