"use client";

import { useEffect, useRef, useState } from "react";

interface TechnicalTimerProps {
  totalSeconds: number; // 3600 for 60 min
  onExpire?: () => void;
}

export default function TechnicalTimer({ totalSeconds, onExpire }: TechnicalTimerProps) {
  const [remaining, setRemaining] = useState(totalSeconds);
  const expiredRef = useRef(false);

  useEffect(() => {
    const id = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(id);
          if (!expiredRef.current) {
            expiredRef.current = true;
            onExpire?.();
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [onExpire]);

  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const isWarning = remaining <= 600;  // last 10 min
  const isCritical = remaining <= 300; // last 5 min
  const pct = Math.round((remaining / totalSeconds) * 100);

  const color = isCritical ? "#FF453A" : isWarning ? "#FF9F0A" : "#30D158";

  return (
    <div
      className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl"
      style={{
        background: isCritical
          ? "rgba(255,69,58,0.1)"
          : isWarning
          ? "rgba(255,159,10,0.08)"
          : "rgba(255,255,255,0.04)",
        border: `1px solid ${isCritical ? "rgba(255,69,58,0.25)" : isWarning ? "rgba(255,159,10,0.2)" : "rgba(255,255,255,0.08)"}`,
      }}
    >
      {/* Ring */}
      <svg width="20" height="20" viewBox="0 0 20 20" style={{ flexShrink: 0 }}>
        <circle cx="10" cy="10" r="8" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="2" />
        <circle
          cx="10"
          cy="10"
          r="8"
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeDasharray={`${2 * Math.PI * 8}`}
          strokeDashoffset={`${2 * Math.PI * 8 * (1 - pct / 100)}`}
          transform="rotate(-90 10 10)"
          style={{ transition: "stroke-dashoffset 1s linear, stroke 0.3s" }}
        />
      </svg>

      <span
        className="font-mono text-[15px] font-semibold tabular-nums"
        style={{ color, letterSpacing: "0.02em" }}
      >
        {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
      </span>
    </div>
  );
}
