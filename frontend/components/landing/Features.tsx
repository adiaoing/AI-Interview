"use client";

import { Brain, Mic, TrendingUp, Zap, Target, Shield } from "lucide-react";

const features = [
  {
    icon: Brain,
    title: "Adaptive Difficulty",
    description: "AI Interview calibrates in real time. Nail an answer and questions get harder. Struggle, and it rebuilds your confidence before moving on.",
    color: "#0A84FF",
  },
  {
    icon: Target,
    title: "RAG Gap Detection",
    description: "Every answer is embedded and stored. The follow-up agent searches your history to surface questions that target recurring weak spots.",
    color: "#5E5CE6",
  },
  {
    icon: Mic,
    title: "Voice-First",
    description: "Speak naturally. AI Interview transcribes in real time with the Web Speech API and responds in a calm, clear voice via ElevenLabs TTS.",
    color: "#30D158",
  },
  {
    icon: Zap,
    title: "Instant Feedback",
    description: "Every answer gets a score 1–5, identified competency, specific strengths and gaps, and a one-line coaching note.",
    color: "#FFD60A",
  },
  {
    icon: TrendingUp,
    title: "Competency Tracking",
    description: "Rolling averages across problem-solving, communication, and technical depth — tracked per session and surfaced in your report.",
    color: "#FF6B6B",
  },
  {
    icon: Shield,
    title: "4-Agent Loop",
    description: "Interviewer, Grader, Follow-up, and Coach agents run in a shared LangGraph session, each with a distinct role and memory access.",
    color: "#FF9F0A",
  },
];

export default function Features() {
  return (
    <section className="py-28 px-6" id="features">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16 max-w-2xl mx-auto">
          <p className="text-[13px] font-medium mb-4 tracking-wide uppercase"
            style={{ color: "#0A84FF", letterSpacing: "0.08em" }}>
            Why AI Interview
          </p>
          <h2
            className="text-[clamp(1.8rem,4vw,2.8rem)] font-bold leading-tight tracking-tight mb-4"
            style={{
              background: "linear-gradient(180deg, #ffffff 0%, rgba(255,255,255,0.7) 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Everything you need to ace your interview with confidence
          </h2>
          <p className="text-base leading-relaxed" style={{ color: "rgba(245,245,247,0.45)" }}>
            AI Interview isn&apos;t a question bank. It&apos;s a simulation built on state-of-the-art multi-agent AI.
          </p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((f, i) => (
            <div
              key={f.title}
              className="group rounded-2xl p-6 transition-all duration-300 cursor-default"
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.06)",
                animationDelay: `${i * 75}ms`,
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.05)";
                (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(255,255,255,0.1)";
                (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.03)";
                (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(255,255,255,0.06)";
                (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
              }}
            >
              {/* Icon */}
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center mb-5"
                style={{
                  background: `${f.color}14`,
                  border: `1px solid ${f.color}22`,
                }}
              >
                <f.icon size={18} style={{ color: f.color }} />
              </div>
              <h3 className="text-[15px] font-semibold mb-2" style={{ color: "rgba(255,255,255,0.9)" }}>
                {f.title}
              </h3>
              <p className="text-[13.5px] leading-relaxed" style={{ color: "rgba(245,245,247,0.45)" }}>
                {f.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
