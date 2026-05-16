import { createClient } from "@/lib/supabase";
import type { DocumentUploadResponse, InterviewType, ReportResponse, StartResponse, TurnResponse } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getUserId(): Promise<string> {
  const supabase = createClient();
  if (!supabase) {
    throw new Error("Supabase auth is not configured.");
  }

  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  if (error) {
    throw new Error(error.message);
  }
  if (!user) {
    throw new Error("Please sign in before starting an interview.");
  }

  return user.id;
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const userId = await getUserId();
  const headers = new Headers(init.headers);
  headers.set("X-User-Id", userId);

  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail ?? payload.message ?? detail;
    } catch {
      // Keep the generic HTTP error.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export async function createSession(
  interviewType: InterviewType,
  role: string | null,
  difficulty: number,
) {
  return apiFetch<{ session_id: string }>("/sessions", {
    method: "POST",
    body: JSON.stringify({
      interview_type: interviewType,
      role,
      difficulty,
    }),
  });
}

export async function startSession(sessionId: string) {
  return apiFetch<StartResponse>(`/sessions/${sessionId}/start`, {
    method: "POST",
  });
}

// 提交纯文本简历，后端会负责持久化、切块和向量化。
export async function uploadResumeText(sessionId: string, content: string) {
  return apiFetch<DocumentUploadResponse>(`/sessions/${sessionId}/resume`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

// 上传 PDF/DOCX 简历文件；由后端完成解析、持久化、切块和向量化。
export async function uploadResumeFile(sessionId: string, file: File) {
  const body = new FormData();
  body.set("file", file);
  return apiFetch<DocumentUploadResponse>(`/sessions/${sessionId}/resume/file`, {
    method: "POST",
    body,
  });
}

// 提交纯文本岗位 JD，后端会负责持久化、切块和向量化。
export async function uploadJobDescriptionText(sessionId: string, content: string) {
  return apiFetch<DocumentUploadResponse>(`/sessions/${sessionId}/job-description`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

// 上传 PDF/DOCX 岗位 JD 文件；由后端完成解析、持久化、切块和向量化。
export async function uploadJobDescriptionFile(sessionId: string, file: File) {
  const body = new FormData();
  body.set("file", file);
  return apiFetch<DocumentUploadResponse>(`/sessions/${sessionId}/job-description/file`, {
    method: "POST",
    body,
  });
}

export async function submitTurn(sessionId: string, answer: string) {
  return apiFetch<TurnResponse>(`/sessions/${sessionId}/turn`, {
    method: "POST",
    body: JSON.stringify({ answer }),
  });
}

export async function getHistory(sessionId: string) {
  return apiFetch<{ messages: import("@/types").Message[] }>(`/sessions/${sessionId}/history`);
}

export async function getReport(sessionId: string) {
  return apiFetch<ReportResponse>(`/sessions/${sessionId}/report`);
}

export async function interruptTTS(sessionId: string) {
  return apiFetch<{ interrupted: boolean; session_id: string }>("/tts/interrupt", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}
