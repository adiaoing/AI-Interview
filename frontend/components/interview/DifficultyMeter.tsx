const DIFFICULTY_LABELS: Record<number, string> = { 1: "Entry", 2: "Junior", 3: "Mid-Level", 4: "Senior", 5: "Staff" };
const DIFFICULTY_COLORS: Record<number, string> = {
  1: "#30D158", 2: "#34C759", 3: "#0A84FF", 4: "#FF9F0A", 5: "#FF453A",
};

interface DifficultyMeterProps {
  difficulty: number;
  turn: number;
  maxTurns: number;
}

export default function DifficultyMeter({ difficulty, turn, maxTurns }: DifficultyMeterProps) {
  const progress = Math.min(Math.round((turn / maxTurns) * 100), 100);
  const color = DIFFICULTY_COLORS[difficulty] ?? "#0A84FF";

  return (
    <div className="space-y-3">
      {/* Row 1: Progress label + count */}
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-medium" style={{ color: "rgba(255,255,255,0.35)" }}>Progress</span>
        <span className="text-[12px] font-medium" style={{ color: "rgba(255,255,255,0.35)" }}>
          {turn}<span style={{ color: "rgba(255,255,255,0.2)" }}>/{maxTurns}</span>
        </span>
      </div>

      {/* Progress bar */}
      <div className="relative h-1 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.07)" }}>
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-700"
          style={{ width: `${progress}%`, background: `linear-gradient(90deg, #0A84FF, ${color})` }}
        />
      </div>

      {/* Row 2: Difficulty label + dots */}
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-medium" style={{ color: "rgba(255,255,255,0.35)" }}>Difficulty</span>
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((d) => (
              <div
                key={d}
                className="w-4 h-1 rounded-full transition-all duration-300"
                style={{ background: d <= difficulty ? color : "rgba(255,255,255,0.1)" }}
              />
            ))}
          </div>
          <span className="text-[11px] font-semibold" style={{ color }}>
            {DIFFICULTY_LABELS[difficulty] ?? "Mid-Level"}
          </span>
        </div>
      </div>
    </div>
  );
}
