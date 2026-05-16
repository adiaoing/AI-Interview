interface QuestionCardProps {
  question: string;
  turn: number;
  difficulty: number;
  isFollowup?: boolean;
}

const difficultyLabel: Record<number, string> = { 1: "Entry", 2: "Junior", 3: "Mid-Level", 4: "Senior", 5: "Staff" };
const difficultyGlow:  Record<number, string> = {
  1: "rgba(48,209,88,0.15)",
  2: "rgba(52,199,89,0.12)",
  3: "rgba(10,132,255,0.12)",
  4: "rgba(255,159,10,0.12)",
  5: "rgba(255,69,58,0.12)",
};
const difficultyColor: Record<number, string> = {
  1: "#30D158", 2: "#34C759", 3: "#0A84FF", 4: "#FF9F0A", 5: "#FF453A",
};

export default function QuestionCard({ question, turn, difficulty, isFollowup }: QuestionCardProps) {
  return (
    <div
      className="rounded-2xl p-6 transition-all duration-300"
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        boxShadow: `0 0 40px ${difficultyGlow[difficulty] ?? "transparent"}`,
      }}
    >
      <div className="flex items-center gap-2.5 mb-5">
        <span className="text-[12px] font-medium" style={{ color: "rgba(255,255,255,0.3)" }}>
          Question {turn}
        </span>
        {isFollowup && (
          <span className="text-[11px] font-medium px-2 py-0.5 rounded-full" style={{ background: "rgba(255,159,10,0.1)", color: "#FF9F0A", border: "1px solid rgba(255,159,10,0.2)" }}>
            Follow-up
          </span>
        )}
        <span
          className="ml-auto text-[11px] font-semibold px-2.5 py-1 rounded-full"
          style={{
            background: `${difficultyColor[difficulty] ?? "#0A84FF"}14`,
            color: difficultyColor[difficulty] ?? "#0A84FF",
            border: `1px solid ${difficultyColor[difficulty] ?? "#0A84FF"}22`,
          }}
        >
          {difficultyLabel[difficulty] ?? "Mid-Level"}
        </span>
      </div>
      <p className="text-[16px] font-medium leading-relaxed" style={{ color: "rgba(255,255,255,0.9)" }}>
        {question}
      </p>
    </div>
  );
}
