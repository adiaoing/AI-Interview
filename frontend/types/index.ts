export type InterviewType = "behavioral" | "technical" | "general";

export interface Session {
  id: string;
  user_id: string;
  interview_type: InterviewType;
  role: string | null;
  difficulty: number;
  status: "active" | "completed";
  turn_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface Message {
  id: string;
  session_id: string;
  role: "interviewer" | "user" | "coach";
  content: string;
  competency: string | null;
  score: number | null;
  turn_number: number;
  is_followup: boolean;
  created_at: string;
}

export interface Grading {
  score: number;
  competency: string;
  feedback: string;
  strengths: string[];
  gaps: string[];
}

export interface RagMatch {
  id: string;
  content: string;
  competency: string | null;
  score: number | null;
  similarity: number | null;
}

export interface UserMemoryMatch {
  id: string;
  memory_type: "profile" | "project" | "strength" | "weakness" | "preference";
  content: string;
  confidence: number | null;
  source_session_id: string | null;
  last_used_at: string | null;
  similarity: number | null;
}

export interface TurnResponse {
  session_complete: boolean;
  grading: Grading;
  coaching_note: string;
  current_rag_matches: RagMatch[];
  current_user_memory_matches?: UserMemoryMatch[];
  recurring_weakness_detected?: boolean;
  question: string | null;
  tts_audio: string | null;
  turn: number;
  difficulty: number;
  is_followup: boolean;
}

export interface StartResponse {
  question: string;
  tts_audio: string | null;
  turn: number;
  difficulty: number;
  session_complete: boolean;
  current_user_memory_matches?: UserMemoryMatch[];
}

export interface DocumentUploadResponse {
  document_id: string;
  chunk_count: number;
  status: "pending" | "processed" | "failed";
}

export interface CompetencyScore {
  competency: string;
  score: number;
  attempts: number;
}

export interface RagInsight {
  turn_number: number;
  question: string;
  recurring_weakness: boolean;
  matches: RagMatch[];
}

export interface ReportResponse {
  session: Session;
  overall_score: number;
  competency_scores: CompetencyScore[];
  coaching_notes: string[];
  rag_insights: RagInsight[];
  user_memory_matches?: UserMemoryMatch[];
  messages: Message[];
  total_turns: number;
}
