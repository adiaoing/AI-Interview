import { ScrollArea } from "@/components/ui/scroll-area";
import type { Message } from "@/types";

interface TranscriptPanelProps { messages: Message[]; }

export default function TranscriptPanel({ messages }: TranscriptPanelProps) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 gap-3">
        <div className="w-10 h-10 rounded-2xl flex items-center justify-center" style={{ background: "rgba(10,132,255,0.08)", border: "1px solid rgba(10,132,255,0.12)" }}>
          <span className="text-lg">💬</span>
        </div>
        <p className="text-[13px]" style={{ color: "rgba(255,255,255,0.25)" }}>Conversation appears here</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-[460px]">
      <div className="space-y-3 pr-2">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className="rounded-xl px-4 py-3 text-[13px]"
            style={{
              background: msg.role === "interviewer"
                ? "rgba(255,255,255,0.04)"
                : msg.role === "coach"
                ? "rgba(10,132,255,0.06)"
                : "rgba(255,255,255,0.02)",
              border: msg.role === "coach"
                ? "1px solid rgba(10,132,255,0.15)"
                : "1px solid rgba(255,255,255,0.05)",
            }}
          >
            <div className="flex items-center gap-2 mb-1.5">
              <span
                className="text-[11px] font-semibold uppercase tracking-wider"
                style={{
                  color: msg.role === "interviewer" ? "rgba(10,132,255,0.8)"
                       : msg.role === "coach"       ? "rgba(94,92,230,0.9)"
                       : "rgba(255,255,255,0.4)",
                  letterSpacing: "0.06em",
                }}
              >
                {msg.role === "interviewer" ? "AI Interview" : msg.role === "coach" ? "Coach" : "You"}
              </span>
              {msg.score != null && (
                <span
                  className="text-[11px] font-medium px-1.5 py-0.5 rounded-md"
                  style={{
                    background: msg.score >= 4 ? "rgba(48,209,88,0.12)" : msg.score >= 3 ? "rgba(255,159,10,0.12)" : "rgba(255,69,58,0.12)",
                    color:      msg.score >= 4 ? "#30D158"               : msg.score >= 3 ? "#FF9F0A"               : "#FF453A",
                  }}
                >
                  {msg.score}/5
                </span>
              )}
              {msg.competency && (
                <span className="text-[11px]" style={{ color: "rgba(255,255,255,0.25)" }}>{msg.competency}</span>
              )}
              {msg.is_followup && (
                <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded-md" style={{ background: "rgba(255,159,10,0.1)", color: "#FF9F0A" }}>↩ follow-up</span>
              )}
            </div>
            <p className="leading-relaxed" style={{ color: "rgba(245,245,247,0.7)" }}>{msg.content}</p>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}
