import Link from "next/link";

export default function Footer() {
  return (
    <footer className="mt-20 py-10 px-6" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-5">
        <div className="flex items-center gap-2">
          <div
            className="w-5 h-5 rounded-md flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, #0A84FF, #5E5CE6)" }}
          >
            <span className="text-white text-[7px] font-bold tracking-tight">AI</span>
          </div>
          <span style={{ fontFamily: "var(--font-brand)", fontSize: "15px", fontWeight: 800, letterSpacing: "-0.03em", color: "rgba(255,255,255,0.45)" }}>AI Interview</span>
        </div>
        <p className="text-[13px]" style={{ color: "rgba(255,255,255,0.18)" }}>
          © {new Date().getFullYear()} AI Interview
        </p>
      </div>
    </footer>
  );
}
