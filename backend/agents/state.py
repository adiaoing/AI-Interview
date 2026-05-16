from __future__ import annotations
from typing import TypedDict


class InterviewState(TypedDict):
    session_id: str
    user_id: str
    interview_type: str          # behavioral | technical | general
    role: str                    # target job role
    difficulty: int              # 1-5, dynamically calibrated
    turn_count: int
    max_turns: int               # configurable session length
    messages: list[dict]         # full conversation history
    competency_scores: dict      # {competency: rolling_score}
    current_question: str
    current_question_is_followup: bool
    current_answer: str
    current_message_id: str | None
    grading: dict                # {score, competency, feedback, strengths, gaps}
    current_rag_matches: list[dict]
    current_user_memory_matches: list[dict]
    recurring_weakness_detected: bool
    rag_insights: list[dict]
    follow_up_needed: bool
    follow_up_question: str
    session_complete: bool
    coaching_notes: list[str]
    tts_audio: str | None        # base64-encoded audio for current question

    # P2: Interview strategy plan from planner_node
    interview_plan: dict         # {strategy, key_competencies, question_sequence, watch_out}
    plan_updated_at: int         # turn_count when plan was last generated/updated

    # P1: Tool calls log from ReAct interviewer (for observability & RAG eval)
    tool_calls_log: list[dict]   # [{tool, args, result_preview, success}]

    # P0: RAG evaluation scores for the current turn
    rag_evaluation: dict         # {context_precision, faithfulness, answer_relevancy}
