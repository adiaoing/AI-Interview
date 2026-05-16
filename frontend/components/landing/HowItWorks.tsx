const steps = [
  {
    n: "01",
    title: "Choose your interview",
    body: "Pick behavioral, technical, or a custom role-based session. Set your starting difficulty from entry-level to staff engineer.",
    detail: "8 questions · ~20 min",
  },
  {
    n: "02",
    title: "Speak your answers",
    body: "AI Interview asks questions and listens in real time. It transcribes, grades, and adapts without you lifting a finger.",
    detail: "Voice + text supported",
  },
  {
    n: "03",
    title: "Get coached every turn",
    body: "After each answer you receive a score, a competency tag, specific gaps, and insight. AI Interview adjusts difficulty automatically.",
    detail: "Instant feedback loop",
  },
];

export default function HowItWorks() {
  return (
    <section className="py-28 px-6 relative overflow-hidden" id="how-it-works">
      {/* Subtle section glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse 80% 50% at 50% 50%, rgba(10,132,255,0.04) 0%, transparent 70%)",
        }}
      />

      <div className="relative max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-20">
          <p className="text-[13px] font-medium mb-4 tracking-widest uppercase"
            style={{ color: "#0A84FF", letterSpacing: "0.08em" }}>
            How it works
          </p>
          <h2
            className="text-[clamp(1.8rem,4vw,2.8rem)] font-bold leading-tight tracking-tight"
            style={{
              background: "linear-gradient(180deg, #ffffff 0%, rgba(255,255,255,0.7) 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Three steps. Real results.
          </h2>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative">
          {/* Connecting line on desktop */}
          <div
            className="hidden md:block absolute top-8 left-1/3 right-1/3 h-px pointer-events-none"
            style={{ background: "linear-gradient(90deg, transparent, rgba(10,132,255,0.25), transparent)" }}
          />

          {steps.map((s, i) => (
            <div key={s.n} className="relative flex flex-col" style={{ animationDelay: `${i * 100}ms` }}>
              <div
                className="rounded-2xl p-7 flex-1"
                style={{
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                {/* Step number */}
                <div
                  className="text-[56px] font-black leading-none mb-5 select-none"
                  style={{
                    background: "linear-gradient(135deg, rgba(10,132,255,0.25), rgba(94,92,230,0.15))",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    backgroundClip: "text",
                  }}
                >
                  {s.n}
                </div>

                <h3
                  className="text-[17px] font-semibold mb-2.5 tracking-tight"
                  style={{ color: "rgba(255,255,255,0.9)" }}
                >
                  {s.title}
                </h3>
                <p className="text-[13.5px] leading-relaxed mb-5" style={{ color: "rgba(245,245,247,0.45)" }}>
                  {s.body}
                </p>
                <span
                  className="inline-block text-[11px] font-medium px-3 py-1 rounded-full tracking-wide"
                  style={{
                    background: "rgba(10,132,255,0.08)",
                    color: "rgba(10,132,255,0.8)",
                    border: "1px solid rgba(10,132,255,0.15)",
                  }}
                >
                  {s.detail}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
