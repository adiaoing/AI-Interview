"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import Link from "next/link";
import TechnicalTimer from "@/components/interview/TechnicalTimer";
import { runCode, type Language, LANGUAGE_LABELS } from "@/lib/piston";

// Dynamically import Monaco to avoid SSR issues
const CodeEditor = dynamic(() => import("@/components/interview/CodeEditor"), { ssr: false, loading: () => (
  <div className="h-full flex items-center justify-center" style={{ background: "rgba(255,255,255,0.02)" }}>
    <p className="text-[13px]" style={{ color: "rgba(255,255,255,0.3)" }}>Loading editor…</p>
  </div>
) });

const LANGUAGES: Language[] = ["python", "javascript"];
const SESSION_MINUTES = 60;

type RunStatus = "idle" | "running" | "passed" | "failed" | "error";

interface TestCase {
  stdin: string;
  expectedOutput: string;
}

interface Example {
  input: string;
  output: string;
  explanation?: string;
}

interface Problem {
  id: number;
  title: string;
  difficulty: "Easy" | "Medium" | "Hard";
  category: string;
  description: string;
  examples: Example[];
  constraints: string[];
  starterCode: Record<string, string>;
  testCases: TestCase[];
}

interface TestResult {
  stdin: string;
  expected: string;
  actual: string;
  passed: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function TechnicalInterviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();

  const [problems, setProblems] = useState<[Problem, Problem] | null>(null);
  const [loadError, setLoadError] = useState("");
  const [activeTab, setActiveTab] = useState<0 | 1>(0);
  const [language, setLanguage] = useState<Language>("python");
  const [codes, setCodes] = useState<[string, string]>(["", ""]);
  const [runStatus, setRunStatus] = useState<[RunStatus, RunStatus]>(["idle", "idle"]);
  const [testResults, setTestResults] = useState<[TestResult[], TestResult[]]>([[], []]);
  const [submitted, setSubmitted] = useState<[boolean, boolean]>([false, false]);
  const [output, setOutput] = useState("");
  const [showOutput, setShowOutput] = useState(false);
  const [expired, setExpired] = useState(false);

  // Fetch problems from backend on mount
  useEffect(() => {
    fetch(`${API_URL}/sessions/${sessionId}/technical-problems`)
      .then((r) => {
        if (!r.ok) throw new Error(`Server error ${r.status}`);
        return r.json();
      })
      .then((data: { problems: Problem[] }) => {
        const [p1, p2] = data.problems;
        setProblems([p1, p2]);
        setCodes([
          p1.starterCode[language] ?? p1.starterCode.python,
          p2.starterCode[language] ?? p2.starterCode.python,
        ]);
      })
      .catch((e) => setLoadError(e.message));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Re-initialize starter code when language changes (after problems are loaded)
  useEffect(() => {
    if (!problems) return;
    setCodes([
      problems[0].starterCode[language] ?? problems[0].starterCode.python,
      problems[1].starterCode[language] ?? problems[1].starterCode.python,
    ]);
    setRunStatus(["idle", "idle"]);
    setTestResults([[], []]);
    setOutput("");
  }, [language, problems]);

  function setActiveCode(val: string) {
    setCodes((prev) => {
      const next: [string, string] = [...prev] as [string, string];
      next[activeTab] = val;
      return next;
    });
  }

  async function handleRun() {
    setRunStatus((prev) => { const n = [...prev] as [RunStatus, RunStatus]; n[activeTab] = "running"; return n; });
    setShowOutput(true);
    setOutput("Running…");

    try {
      const cases = activeProblem.testCases;
      const results: TestResult[] = [];

      for (const tc of cases) {
        const res = await runCode(language, activeCode, tc.stdin);
        const actual = res.stdout.trim();
        const expected = tc.expectedOutput.trim();
        results.push({
          stdin: tc.stdin,
          expected,
          actual,
          passed: actual === expected,
        });
        if (res.stderr) {
          setOutput(res.stderr);
        }
      }

      const allPassed = results.every((r) => r.passed);
      setRunStatus((prev) => { const n = [...prev] as [RunStatus, RunStatus]; n[activeTab] = allPassed ? "passed" : "failed"; return n; });
      setTestResults((prev) => { const n = [...prev] as [TestResult[], TestResult[]]; n[activeTab] = results; return n; });
      setOutput(results.map((r, i) => `Case ${i + 1}: ${r.passed ? "✓ Passed" : "✗ Failed"}\n  Expected: ${r.expected}\n  Got:      ${r.actual}`).join("\n\n"));
    } catch (e) {
      setRunStatus((prev) => { const n = [...prev] as [RunStatus, RunStatus]; n[activeTab] = "error"; return n; });
      setOutput(e instanceof Error ? e.message : "Execution error");
    }
  }

  async function handleSubmit() {
    if (submitted[activeTab]) return;
    await handleRun();
    setSubmitted((prev) => { const n = [...prev] as [boolean, boolean]; n[activeTab] = true; return n; });
  }

  function handleExpire() {
    setExpired(true);
    setTimeout(() => router.push(`/report/${sessionId}`), 3000);
  }

  const statusColor: Record<RunStatus, string> = {
    idle: "rgba(255,255,255,0.3)",
    running: "#0A84FF",
    passed: "#30D158",
    failed: "#FF9F0A",
    error: "#FF453A",
  };
  const statusLabel: Record<RunStatus, string> = {
    idle: "",
    running: "Running…",
    passed: "All tests passed",
    failed: "Some tests failed",
    error: "Runtime error",
  };

  const diffColor = (d: string) =>
    d === "Easy" ? "#30D158" : d === "Medium" ? "#FF9F0A" : "#FF453A";

  // Loading / error state
  if (loadError) {
    return (
      <div className="flex h-screen bg-black items-center justify-center">
        <div className="text-center">
          <p className="text-[16px] font-semibold text-white mb-2">Failed to load problems</p>
          <p className="text-[13px]" style={{ color: "rgba(255,255,255,0.4)" }}>{loadError}</p>
        </div>
      </div>
    );
  }

  if (!problems) {
    return (
      <div className="flex h-screen bg-black items-center justify-center">
        <p className="text-[14px]" style={{ color: "rgba(255,255,255,0.3)" }}>Loading problems…</p>
      </div>
    );
  }

  // problems is guaranteed non-null below this point
  const activeProblem = problems[activeTab];
  const activeCode = codes[activeTab];

  return (
    <div className="flex flex-col h-screen bg-black overflow-hidden">
      {/* ── Top bar ── */}
      <div
        className="flex items-center gap-3 px-4 shrink-0"
        style={{ height: "52px", borderBottom: "1px solid rgba(255,255,255,0.07)", background: "rgba(0,0,0,0.8)", backdropFilter: "blur(20px)" }}
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 mr-2">
          <div className="w-6 h-6 rounded-md flex items-center justify-center" style={{ background: "linear-gradient(135deg, #0A84FF, #5E5CE6)" }}>
            <span className="text-white text-[8px] font-bold tracking-tight">AI</span>
          </div>
          <span className="text-white/70 text-[13px]" style={{ fontFamily: "var(--font-brand)", fontWeight: 800, letterSpacing: "-0.02em" }}>
            AI Interview
          </span>
        </Link>

        {/* Problem tabs */}
        <div
          className="flex rounded-lg overflow-hidden"
          style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}
        >
          {([0, 1] as const).map((i) => (
            <button
              key={i}
              onClick={() => setActiveTab(i)}
              className="flex items-center gap-2 px-3.5 py-1.5 text-[12px] font-medium transition-all duration-150"
              style={{
                background: activeTab === i ? "rgba(10,132,255,0.15)" : "transparent",
                color: activeTab === i ? "#0A84FF" : "rgba(255,255,255,0.4)",
                borderRight: i === 0 ? "1px solid rgba(255,255,255,0.08)" : "none",
              }}
            >
              <span>Q{i + 1}</span>
              {submitted[i] && (
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: runStatus[i] === "passed" ? "#30D158" : "#FF9F0A" }} />
              )}
              <span
                className="text-[10px] px-1 rounded"
                style={{
                  background: `${diffColor(problems[i].difficulty)}15`,
                  color: diffColor(problems[i].difficulty),
                }}
              >
                {problems[i].difficulty}
              </span>
            </button>
          ))}
        </div>

        {/* Language selector */}
        <div className="ml-auto flex items-center gap-2">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            className="text-[12px] font-medium px-2.5 py-1.5 rounded-lg cursor-pointer"
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "rgba(255,255,255,0.75)",
              outline: "none",
            }}
          >
            {LANGUAGES.map((l) => (
              <option key={l} value={l} style={{ background: "#1a1a1a" }}>
                {LANGUAGE_LABELS[l]}
              </option>
            ))}
          </select>

          {/* Run */}
          <button
            onClick={handleRun}
            disabled={runStatus[activeTab] === "running"}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-all duration-150 disabled:opacity-40"
            style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.85)" }}
          >
            <svg width="11" height="12" viewBox="0 0 11 12" fill="none">
              <path d="M1 1.5L10 6L1 10.5V1.5Z" fill="currentColor" />
            </svg>
            Run
          </button>

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={submitted[activeTab] || runStatus[activeTab] === "running"}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[12px] font-semibold transition-all duration-150 disabled:opacity-40 text-white"
            style={{
              background: submitted[activeTab] ? "rgba(48,209,88,0.15)" : "#0A84FF",
              border: submitted[activeTab] ? "1px solid rgba(48,209,88,0.3)" : "none",
              color: submitted[activeTab] ? "#30D158" : "white",
              boxShadow: submitted[activeTab] ? "none" : "0 2px 10px rgba(10,132,255,0.3)",
            }}
          >
            {submitted[activeTab] ? "✓ Submitted" : "Submit"}
          </button>
        </div>

        {/* Timer */}
        <TechnicalTimer totalSeconds={SESSION_MINUTES * 60} onExpire={handleExpire} />
      </div>

      {/* Expired overlay */}
      {expired && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.85)", backdropFilter: "blur(20px)" }}>
          <div className="text-center">
            <p className="text-[32px] font-bold text-white mb-2">Time&apos;s up!</p>
            <p className="text-[15px]" style={{ color: "rgba(255,255,255,0.45)" }}>Redirecting to your report…</p>
          </div>
        </div>
      )}

      {/* ── Main content ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left: Problem panel */}
        <div
          className="w-[42%] shrink-0 overflow-y-auto px-6 py-5"
          style={{ borderRight: "1px solid rgba(255,255,255,0.07)" }}
        >
          {/* Title + difficulty */}
          <div className="flex items-start gap-3 mb-4">
            <div>
              <div className="flex items-center gap-2.5 mb-1.5">
                <span className="text-[12px]" style={{ color: "rgba(255,255,255,0.3)" }}>
                  {activeProblem.id}.
                </span>
                <h1 className="text-[17px] font-semibold text-white leading-snug">{activeProblem.title}</h1>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
                  style={{ background: `${diffColor(activeProblem.difficulty)}15`, color: diffColor(activeProblem.difficulty) }}
                >
                  {activeProblem.difficulty}
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.4)" }}>
                  {activeProblem.category}
                </span>
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="text-[13.5px] leading-relaxed mb-5 whitespace-pre-wrap" style={{ color: "rgba(245,245,247,0.75)" }}>
            {activeProblem.description}
          </div>

          {/* Examples */}
          <div className="space-y-3 mb-5">
            {activeProblem.examples.map((ex, i) => (
              <div key={i} className="rounded-xl overflow-hidden" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                <div className="px-4 pt-3 pb-1">
                  <p className="text-[11px] font-semibold uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.25)", letterSpacing: "0.06em" }}>
                    Example {i + 1}
                  </p>
                  <p className="font-mono text-[12px] mb-1" style={{ color: "rgba(245,245,247,0.7)" }}>
                    <span style={{ color: "rgba(255,255,255,0.35)" }}>Input: </span>{ex.input}
                  </p>
                  <p className="font-mono text-[12px] mb-1" style={{ color: "rgba(245,245,247,0.7)" }}>
                    <span style={{ color: "rgba(255,255,255,0.35)" }}>Output: </span>{ex.output}
                  </p>
                  {ex.explanation && (
                    <p className="text-[12px] mt-1.5 pb-2" style={{ color: "rgba(255,255,255,0.35)" }}>
                      {ex.explanation}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Constraints */}
          <div className="mb-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.25)", letterSpacing: "0.06em" }}>
              Constraints
            </p>
            <ul className="space-y-1">
              {activeProblem.constraints.map((c, i) => (
                <li key={i} className="text-[12.5px] font-mono flex gap-2" style={{ color: "rgba(245,245,247,0.5)" }}>
                  <span style={{ color: "rgba(10,132,255,0.6)" }}>·</span>
                  {c}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right: Editor + output */}
        <div className="flex-1 flex flex-col overflow-hidden">

          {/* Editor */}
          <div className="flex-1 p-3 overflow-hidden">
            <CodeEditor code={activeCode} language={language} onChange={setActiveCode} />
          </div>

          {/* Output drawer */}
          <div
            className="shrink-0 transition-all duration-300 overflow-hidden"
            style={{
              height: showOutput ? "220px" : "42px",
              borderTop: "1px solid rgba(255,255,255,0.07)",
            }}
          >
            {/* Drawer header */}
            <button
              onClick={() => setShowOutput((v) => !v)}
              className="w-full flex items-center gap-3 px-4 h-[42px]"
              style={{ background: "rgba(255,255,255,0.02)" }}
            >
              <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "rgba(255,255,255,0.3)", letterSpacing: "0.06em" }}>
                Output
              </span>
              {runStatus[activeTab] !== "idle" && runStatus[activeTab] !== "running" && (
                <span className="text-[11px] font-medium" style={{ color: statusColor[runStatus[activeTab]] }}>
                  {statusLabel[runStatus[activeTab]]}
                </span>
              )}
              <svg
                className="ml-auto transition-transform duration-200"
                style={{ transform: showOutput ? "rotate(180deg)" : "rotate(0deg)" }}
                width="12" height="12" viewBox="0 0 12 12" fill="none"
              >
                <path d="M2 4.5L6 8L10 4.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>

            {/* Drawer content */}
            {showOutput && (
              <div
                className="px-4 pb-4 h-[178px] overflow-y-auto font-mono text-[12px] leading-relaxed"
                style={{ color: "rgba(245,245,247,0.65)" }}
              >
                {runStatus[activeTab] === "running" ? (
                  <span style={{ color: "#0A84FF", animation: "glow-pulse 1.2s ease-in-out infinite" }}>Executing…</span>
                ) : output ? (
                  <pre className="whitespace-pre-wrap">{output}</pre>
                ) : (
                  <span style={{ color: "rgba(255,255,255,0.2)" }}>Run your code to see output here.</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
