"use client";

import { useEffect, useRef, useState } from "react";

// Web Speech API – not fully typed in all TS DOM lib versions
type SpeechRecognitionCtor = new () => SpeechRecognitionInstance;
interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}
interface SpeechRecognitionResultEvent {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}

interface AudioRecorderProps {
  onSubmit: (transcript: string) => void;
  disabled?: boolean;
}

export default function AudioRecorder({ onSubmit, disabled }: AudioRecorderProps) {
  const [transcript, setTranscript] = useState("");
  const [listening, setListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  useEffect(() => {
    const w = window as typeof window & {
      SpeechRecognition?: SpeechRecognitionCtor;
      webkitSpeechRecognition?: SpeechRecognitionCtor;
    };
    const SpeechRecognitionClass = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (SpeechRecognitionClass) {
      setSpeechSupported(true);
      const rec = new SpeechRecognitionClass();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "en-US";
      rec.onresult = (event: SpeechRecognitionResultEvent) => {
        const results = event.results as ArrayLike<ArrayLike<{ transcript: string }>>;
        let full = "";
        for (let i = 0; i < (results as unknown as { length: number }).length; i++) {
          full += results[i][0].transcript;
        }
        setTranscript(full);
      };
      rec.onend = () => setListening(false);
      recognitionRef.current = rec;
    }
  }, []);

  function toggleListening() {
    if (!recognitionRef.current) return;
    if (listening) {
      recognitionRef.current.stop();
    } else {
      setTranscript("");
      recognitionRef.current.start();
      setListening(true);
    }
  }

  function handleSubmit() {
    if (listening) recognitionRef.current?.stop();
    const text = transcript.trim();
    if (!text) return;
    onSubmit(text);
    setTranscript("");
  }

  return (
    <div className="space-y-3">
      {/* Textarea */}
      <div className="relative">
        <textarea
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder={speechSupported ? "Click the mic to speak, or type your answer…" : "Type your answer here…"}
          disabled={disabled}
          rows={4}
          className="input-apple w-full rounded-xl px-4 py-3 text-[14px] resize-none leading-relaxed"
          style={{ minHeight: "110px", color: "rgba(245,245,247,0.85)" }}
        />
        {listening && (
          <div
            className="absolute bottom-3 right-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full"
            style={{ background: "rgba(255,69,58,0.12)", border: "1px solid rgba(255,69,58,0.2)" }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: "#FF453A", animation: "glow-pulse 1.2s ease-in-out infinite" }}
            />
            <span className="text-[11px] font-medium" style={{ color: "#FF453A" }}>Listening</span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2.5">
        {speechSupported && (
          <button
            type="button"
            onClick={toggleListening}
            disabled={disabled}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-[13px] font-medium transition-all duration-200 disabled:opacity-40"
            style={{
              background: listening ? "rgba(255,69,58,0.12)" : "rgba(255,255,255,0.06)",
              border: listening ? "1px solid rgba(255,69,58,0.25)" : "1px solid rgba(255,255,255,0.1)",
              color: listening ? "#FF453A" : "rgba(255,255,255,0.7)",
            }}
          >
            {listening ? (
              <>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <rect x="3" y="3" width="8" height="8" rx="1.5" fill="currentColor"/>
                </svg>
                Stop
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <rect x="5" y="1" width="4" height="8" rx="2" fill="currentColor"/>
                  <path d="M2 7.5C2 10.537 4.239 13 7 13s5-2.463 5-5.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                  <line x1="7" y1="13" x2="7" y2="14" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                </svg>
                Record
              </>
            )}
          </button>
        )}

        <button
          type="button"
          onClick={handleSubmit}
          disabled={disabled || !transcript.trim()}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-[13px] font-semibold text-white transition-all duration-200 disabled:opacity-40 active:scale-[0.98]"
          style={{ background: "#0A84FF", boxShadow: transcript.trim() ? "0 0 0 1px rgba(10,132,255,0.3), 0 4px 16px rgba(10,132,255,0.25)" : "none" }}
        >
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M1 6.5h11M7 1.5l5 5-5 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Submit
        </button>

        {transcript.trim() && !listening && (
          <button
            type="button"
            onClick={() => setTranscript("")}
            className="px-3 py-2 rounded-xl text-[12px] transition-all duration-200"
            style={{ color: "rgba(255,255,255,0.3)", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
}
