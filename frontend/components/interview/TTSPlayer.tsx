"use client";

import { useEffect, useRef, useState } from "react";
import { interruptTTS } from "@/lib/api";

interface TTSPlayerProps {
  audio: string | null;
  text: string;
  sessionId: string;
  onPlaybackEnd?: () => void;
}

export default function TTSPlayer({ audio, text, sessionId, onPlaybackEnd }: TTSPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!audio) {
      onPlaybackEnd?.();
      return;
    }
    const blob = base64ToBlob(audio, "audio/mpeg");
    const url = URL.createObjectURL(blob);
    const el = new Audio(url);
    audioRef.current = el;
    el.onplay = () => setPlaying(true);
    el.onended = () => { setPlaying(false); URL.revokeObjectURL(url); onPlaybackEnd?.(); };
    el.onerror = () => { setPlaying(false); URL.revokeObjectURL(url); onPlaybackEnd?.(); };
    el.play().catch(() => { setPlaying(false); onPlaybackEnd?.(); });
    return () => { el.pause(); URL.revokeObjectURL(url); };
  }, [audio]);

  async function handleInterrupt() {
    audioRef.current?.pause();
    setPlaying(false);
    await interruptTTS(sessionId);
    onPlaybackEnd?.();
  }

  if (!playing && audio) return null;

  return (
    <div className="flex items-center gap-3">
      {playing ? (
        <div
          className="flex items-center gap-3 px-4 py-2.5 rounded-xl"
          style={{ background: "rgba(10,132,255,0.08)", border: "1px solid rgba(10,132,255,0.15)" }}
        >
          {/* Animated waveform bars */}
          <div className="flex items-center gap-0.5">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="w-0.5 rounded-full"
                style={{
                  background: "#0A84FF",
                  height: `${[12, 18, 14, 10][i]}px`,
                  animation: `glow-pulse ${0.8 + i * 0.15}s ease-in-out infinite`,
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </div>
          <span className="text-[13px] font-medium" style={{ color: "rgba(10,132,255,0.9)" }}>
            AI Interview is speaking
          </span>
          <button
            onClick={handleInterrupt}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[12px] font-medium transition-all duration-200"
            style={{ background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.5)", border: "1px solid rgba(255,255,255,0.1)" }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <rect x="1" y="1" width="8" height="8" rx="1.5" fill="currentColor"/>
            </svg>
            Stop
          </button>
        </div>
      ) : !audio ? (
        <div
          className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl"
          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 5h3l3-3v10l-3-3H2V5z" fill="rgba(255,255,255,0.3)"/>
            <path d="M9 4.5c1.1.9 1.8 2.2 1.8 3.5S10.1 10.6 9 11.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.2" strokeLinecap="round"/>
          </svg>
          <span className="text-[12px] italic" style={{ color: "rgba(255,255,255,0.3)" }}>Voice unavailable — reading mode</span>
        </div>
      ) : null}
    </div>
  );
}

function base64ToBlob(base64: string, mimeType: string): Blob {
  const byteChars = atob(base64);
  const byteNums = Array.from(byteChars).map((c) => c.charCodeAt(0));
  return new Blob([new Uint8Array(byteNums)], { type: mimeType });
}
