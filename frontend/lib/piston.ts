export type Language = "python" | "javascript";

export const LANGUAGE_LABELS: Record<Language, string> = {
  python: "Python",
  javascript: "JavaScript",
};

export const MONACO_LANGUAGE_MAP: Record<Language, string> = {
  python: "python",
  javascript: "javascript",
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function runCode(language: Language, code: string, stdin = "") {
  const response = await fetch(`${API_URL}/sessions/run-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      language,
      code,
      stdin,
    }),
  });

  if (!response.ok) {
    let detail = `Code execution failed (${response.status})`;
    try {
      const payload = await response.json();
      detail = payload.detail ?? detail;
    } catch {
      // Keep the generic HTTP error.
    }
    throw new Error(detail);
  }

  const payload = await response.json();
  return {
    stdout: payload.stdout ?? "",
    stderr: payload.stderr ?? "",
    code: payload.code ?? 0,
    signal: payload.signal ?? null,
  };
}
