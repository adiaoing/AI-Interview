"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/layout/Navbar";
import TranscriptPanel from "@/components/interview/TranscriptPanel";
import { getReport } from "@/lib/api";
import type { ReportResponse } from "@/types";

const scoreColor = (s: number) =>
  s >= 4 ? "#30D158" : s >= 3 ? "#FF9F0A" : "#FF453A";
const scoreBg = (s: number) =>
  s >= 4 ? "rgba(48,209,88,0.1)" : s >= 3 ? "rgba(255,159,10,0.1)" : "rgba(255,69,58,0.1)";
const scoreLabel = (s: number) =>
  s >= 4 ? "Strong" : s >= 3 ? "Solid" : "Needs work";

export default function ReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getReport(sessionId)
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) {
    return (
      <>
        <Navbar />
        <main className="min-h-screen bg-black pt-24 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <div
              className="w-10 h-10 rounded-2xl flex items-center justify-center"
              style={{ background: "rgba(10,132,255,0.1)", border: "1px solid rgba(10,132,255,0.2)", animation: "glow-pulse 1.5s ease-in-out infinite" }}
            >
              <span className="text-lg">📊</span>
            </div>
            <p className="text-[14px]" style={{ color: "rgba(255,255,255,0.35)" }}>Generating your report…</p>
          </div>
        </main>
      </>
    );
  }

  if (error || !report) {
    return (
      <>
        <Navbar />
        <main className="min-h-screen bg-black pt-24 flex items-center justify-center">
          <p className="text-[14px]" style={{ color: "#FF453A" }}>{error || "Report not found."}</p>
        </main>
      </>
    );
  }

  const overall = report.overall_score;
  const overallPct = Math.min(Math.round((overall / 5) * 100), 100);
  const typeLabel = report.session.interview_type.charAt(0).toUpperCase() + report.session.interview_type.slice(1);

  return (
    <>
      <Navbar />
      <div className="fixed inset-0 pointer-events-none" style={{ background: "radial-gradient(ellipse 50% 35% at 50% 0%, rgba(10,132,255,0.05) 0%, transparent 55%)" }} />

      <main className="relative min-h-screen bg-black pt-20 pb-16 px-4">
        <div className="max-w-3xl mx-auto space-y-5">

          {/* Header */}
          <div className="pt-6 pb-2">
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wider mb-4"
              style={{ background: "rgba(10,132,255,0.1)", color: "rgba(10,132,255,0.85)", border: "1px solid rgba(10,132,255,0.2)", letterSpacing: "0.06em" }}
            >
              Interview complete
            </div>
            <h1 className="text-[28px] font-bold text-white tracking-tight mb-1">Your Results</h1>
            <p className="text-[14px]" style={{ color: "rgba(245,245,247,0.4)" }}>
              {typeLabel} interview
              {report.session.role ? ` · ${report.session.role}` : ""}
              {" · "}{report.total_turns} question{report.total_turns !== 1 ? "s" : ""} answered
            </p>
          </div>

          {/* Overall score card */}
          <div
            className="rounded-2xl p-6"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}
          >
            <p
              className="text-[11px] font-semibold uppercase tracking-wider mb-5"
              style={{ color: "rgba(255,255,255,0.3)", letterSpacing: "0.07em" }}
            >
              Overall performance
            </p>
            <div className="flex items-end gap-4 mb-5">
              <span className="text-[56px] font-bold leading-none" style={{ color: scoreColor(overall) }}>
                {overall.toFixed(1)}
              </span>
              <span className="text-[20px] mb-1" style={{ color: "rgba(255,255,255,0.25)" }}>/5</span>
              <div
                className="ml-auto px-3 py-1 rounded-full text-[12px] font-semibold"
                style={{ background: scoreBg(overall), color: scoreColor(overall), border: `1px solid ${scoreColor(overall)}22` }}
              >
                {scoreLabel(overall)}
              </div>
            </div>
            {/* Progress bar */}
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.07)" }}>
              <div
                className="h-full rounded-full transition-all duration-1000"
                style={{ width: `${overallPct}%`, background: `linear-gradient(90deg, #0A84FF, ${scoreColor(overall)})` }}
              />
            </div>
          </div>

          {/* Competency breakdown */}
          {report.competency_scores.length > 0 && (
            <div
              className="rounded-2xl p-6"
              style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}
            >
              <p
                className="text-[11px] font-semibold uppercase tracking-wider mb-5"
                style={{ color: "rgba(255,255,255,0.3)", letterSpacing: "0.07em" }}
              >
                Competency breakdown
              </p>
              <div className="space-y-4">
                {report.competency_scores
                  .sort((a, b) => b.score - a.score)
                  .map((c) => {
                    const pct = Math.min(Math.round((c.score / 5) * 100), 100);
                    const col = scoreColor(c.score);
                    return (
                      <div key={c.competency} className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[13px] font-medium capitalize" style={{ color: "rgba(255,255,255,0.75)" }}>
                            {c.competency}
                          </span>
                          <span className="text-[12px]" style={{ color: "rgba(255,255,255,0.35)" }}>
                            {Number(c.score).toFixed(1)}/5
                            <span className="ml-1.5" style={{ color: "rgba(255,255,255,0.2)" }}>
                              · {c.attempts} answer{c.attempts !== 1 ? "s" : ""}
                            </span>
                          </span>
                        </div>
                        <div className="h-1 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.07)" }}>
                          <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{ width: `${pct}%`, background: col }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Coaching insights */}
          {report.coaching_notes.length > 0 && (
            <div
              className="rounded-2xl p-6"
              style={{ background: "rgba(94,92,230,0.05)", border: "1px solid rgba(94,92,230,0.12)" }}
            >
              <p
                className="text-[11px] font-semibold uppercase tracking-wider mb-5"
                style={{ color: "rgba(94,92,230,0.7)", letterSpacing: "0.07em" }}
              >
                Coaching insights
              </p>
              <ul className="space-y-4">
                {report.coaching_notes.map((note, i) => (
                  <li key={i} className="flex gap-4">
                    <span
                      className="text-[13px] font-bold shrink-0 w-6 text-right"
                      style={{ color: "rgba(94,92,230,0.5)" }}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <p className="text-[13px] leading-relaxed" style={{ color: "rgba(245,245,247,0.65)" }}>{note}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 历史弱点命中：展示重复出现的相似问题与相关片段。 */}
          <div
            className="rounded-2xl p-6"
            style={{ background: "rgba(10,132,255,0.04)", border: "1px solid rgba(10,132,255,0.12)" }}
          >
            <p
              className="text-[11px] font-semibold uppercase tracking-wider mb-5"
              style={{ color: "rgba(10,132,255,0.75)", letterSpacing: "0.07em" }}
            >
              历史相似弱点
            </p>
            {report.rag_insights.length > 0 ? (
              <div className="space-y-5">
                {report.rag_insights.map((insight, index) => (
                  <div key={`${insight.turn_number}-${index}`} className="space-y-3">
                    <p className="text-[13px] leading-relaxed" style={{ color: "rgba(245,245,247,0.72)" }}>
                      第 {insight.turn_number} 轮：{insight.question}
                    </p>
                    <div className="space-y-2">
                      {insight.matches.slice(0, 2).map((match, matchIndex) => (
                        <div
                          key={`${match.id}-${matchIndex}`}
                          className="rounded-lg p-3"
                          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
                        >
                          <p className="text-[12px] mb-1" style={{ color: "rgba(10,132,255,0.85)" }}>
                            {match.competency || "未知能力项"}
                            {match.score !== null ? ` · 历史分数 ${match.score}/5` : ""}
                            {match.similarity !== null ? ` · 相似度 ${match.similarity.toFixed(2)}` : ""}
                          </p>
                          <p className="text-[12px] leading-relaxed" style={{ color: "rgba(245,245,247,0.55)" }}>
                            {match.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[13px] leading-relaxed" style={{ color: "rgba(245,245,247,0.48)" }}>
                当前报告未命中可复用的历史弱点或长期记忆，说明本场面试暂未召回到和本轮表现高度相关的跨 session 画像。
              </p>
            )}
          </div>

          {report.user_memory_matches && report.user_memory_matches.length > 0 && (
            <div
              className="rounded-2xl p-6"
              style={{ background: "rgba(94,92,230,0.05)", border: "1px solid rgba(94,92,230,0.12)" }}
            >
              <p
                className="text-[11px] font-semibold uppercase tracking-wider mb-5"
                style={{ color: "rgba(94,92,230,0.78)", letterSpacing: "0.07em" }}
              >
                Cross-session memory
              </p>
              <div className="space-y-3">
                {report.user_memory_matches.slice(0, 4).map((memory, index) => (
                  <div
                    key={`${memory.id}-${index}`}
                    className="rounded-lg p-3"
                    style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
                  >
                    <p className="text-[12px] mb-1" style={{ color: "rgba(94,92,230,0.85)" }}>
                      {memory.memory_type}
                      {memory.confidence !== null ? ` 路 置信度 ${memory.confidence.toFixed(2)}` : ""}
                      {memory.similarity !== null ? ` 路 相似度 ${memory.similarity.toFixed(2)}` : ""}
                    </p>
                    <p className="text-[12px] leading-relaxed" style={{ color: "rgba(245,245,247,0.58)" }}>
                      {memory.content}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Divider */}
          <div style={{ height: "1px", background: "rgba(255,255,255,0.06)" }} />

          {/* Full transcript */}
          <div
            className="rounded-2xl p-6"
            style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}
          >
            <p
              className="text-[11px] font-semibold uppercase tracking-wider mb-4"
              style={{ color: "rgba(255,255,255,0.25)", letterSpacing: "0.07em" }}
            >
              Full transcript
            </p>
            <TranscriptPanel messages={report.messages} />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <Link
              href="/interview/setup"
              className="flex-1 py-3 rounded-2xl text-[14px] font-semibold text-white text-center transition-all duration-200 active:scale-[0.99]"
              style={{ background: "#0A84FF", boxShadow: "0 0 0 1px rgba(10,132,255,0.3), 0 4px 20px rgba(10,132,255,0.25)" }}
            >
              Practice again
            </Link>
            <Link
              href="/"
              className="flex-1 py-3 rounded-2xl text-[14px] font-semibold text-center transition-all duration-200"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.7)" }}
            >
              Back to home
            </Link>
          </div>

        </div>
      </main>
    </>
  );
}
