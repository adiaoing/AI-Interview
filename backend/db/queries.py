from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any
from db.client import get_client


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(user_id: str, interview_type: str, role: str | None) -> dict:
    db = get_client()
    result = (
        db.table("sessions")
        .insert({
            "user_id": user_id,
            "interview_type": interview_type,
            "role": role,
        })
        .execute()
    )
    return result.data[0]


def get_session(session_id: str) -> dict | None:
    db = get_client()
    result = (
        db.table("sessions")
        .select("*")
        .eq("id", session_id)
        .maybe_single()
        .execute()
    )
    return result.data


def update_session(session_id: str, updates: dict) -> dict:
    db = get_client()
    result = (
        db.table("sessions")
        .update(updates)
        .eq("id", session_id)
        .execute()
    )
    return result.data[0]


def complete_session(session_id: str, difficulty: int) -> dict:
    return update_session(session_id, {
        "status": "completed",
        "difficulty": difficulty,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })


# ── Messages ──────────────────────────────────────────────────────────────────

def save_message(
    session_id: str,
    role: str,
    content: str,
    turn_number: int,
    competency: str | None = None,
    score: int | None = None,
    is_followup: bool = False,
) -> dict:
    db = get_client()
    result = (
        db.table("messages")
        .insert({
            "session_id": session_id,
            "role": role,
            "content": content,
            "competency": competency,
            "score": score,
            "turn_number": turn_number,
            "is_followup": is_followup,
        })
        .execute()
    )
    return result.data[0]


def get_messages(session_id: str) -> list[dict]:
    db = get_client()
    result = (
        db.table("messages")
        .select("*")
        .eq("session_id", session_id)
        .order("turn_number")
        .execute()
    )
    return result.data


# ── Competency scores ─────────────────────────────────────────────────────────

def upsert_competency_score(session_id: str, competency: str, score: float) -> dict:
    db = get_client()
    existing = (
        db.table("competency_scores")
        .select("*")
        .eq("session_id", session_id)
        .eq("competency", competency)
        .maybe_single()
        .execute()
    )
    if existing.data:
        attempts = existing.data["attempts"] + 1
        rolling_score = (existing.data["score"] * existing.data["attempts"] + score) / attempts
        result = (
            db.table("competency_scores")
            .update({
                "score": rolling_score,
                "attempts": attempts,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("session_id", session_id)
            .eq("competency", competency)
            .execute()
        )
    else:
        result = (
            db.table("competency_scores")
            .insert({
                "session_id": session_id,
                "competency": competency,
                "score": score,
                "attempts": 1,
            })
            .execute()
        )
    return result.data[0]


def get_competency_scores(session_id: str) -> list[dict]:
    db = get_client()
    result = (
        db.table("competency_scores")
        .select("*")
        .eq("session_id", session_id)
        .execute()
    )
    return result.data


# ── Embeddings ────────────────────────────────────────────────────────────────

def save_session_state_snapshot(
    session_id: str,
    user_id: str,
    turn_number: int,
    state: dict,
    snapshot_stage: str = "turn",
) -> dict:
    """保存会话状态快照，供短期记忆恢复使用。"""
    db = get_client()
    result = (
        db.table("session_state_snapshots")
        .insert({
            "session_id": session_id,
            "user_id": user_id,
            "turn_number": turn_number,
            "snapshot_stage": snapshot_stage,
            "state": state,
        })
        .execute()
    )
    return result.data[0]


def get_latest_session_state_snapshot(session_id: str) -> dict | None:
    """读取某个 session 最新的状态快照。"""
    db = get_client()
    result = (
        db.table("session_state_snapshots")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def save_user_memory(
    user_id: str,
    memory_type: str,
    content: str,
    embedding: list[float],
    source_session_id: str | None,
    confidence: float,
) -> dict:
    db = get_client()
    normalized_content = content.strip()
    existing = (
        db.table("user_memories")
        .select("*")
        .eq("user_id", user_id)
        .eq("memory_type", memory_type)
        .eq("content", normalized_content)
        .limit(1)
        .execute()
    )
    existing_rows = existing.data or []
    payload = {
        "user_id": user_id,
        "memory_type": memory_type,
        "content": normalized_content,
        "embedding": embedding,
        "source_session_id": source_session_id,
        "confidence": confidence,
        "last_used_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if existing_rows:
        current = existing_rows[0]
        result = (
            db.table("user_memories")
            .update({
                **payload,
                "confidence": max(float(current.get("confidence") or 0), confidence),
            })
            .eq("id", current["id"])
            .execute()
        )
    else:
        result = db.table("user_memories").insert(payload).execute()
    return result.data[0]


def find_similar_user_memories(
    user_id: str,
    query_embedding: list[float],
    threshold: float = 0.72,
    limit: int = 4,
    memory_types: list[str] | None = None,
) -> list[dict]:
    result = get_client().rpc(
        "match_user_memories",
        {
            "p_user_id": user_id,
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
            "p_memory_types": memory_types,
        },
    ).execute()
    return result.data or []


def touch_user_memories(memory_ids: list[str]) -> None:
    if not memory_ids:
        return
    now = datetime.now(timezone.utc).isoformat()
    db = get_client()
    for memory_id in memory_ids:
        db.table("user_memories").update({"last_used_at": now}).eq("id", memory_id).execute()


def save_rag_evaluation(
    session_id: str,
    turn_number: int,
    metrics: dict,
    tool_calls: list[dict] | None = None,
    message_id: str | None = None,
) -> dict:
    """持久化一轮 RAG 评估结果。"""
    db = get_client()
    result = db.table("rag_evaluations").insert({
        "session_id": session_id,
        "message_id": message_id,
        "turn_number": turn_number,
        "context_precision": metrics.get("context_precision"),
        "faithfulness": metrics.get("faithfulness"),
        "answer_relevancy": metrics.get("answer_relevancy"),
        "aggregate_score": metrics.get("aggregate_score"),
        "weakness_detection_outcome": (metrics.get("weakness_detection") or {}).get("outcome"),
        "weakness_detection_correct": (metrics.get("weakness_detection") or {}).get("correct"),
        "retrieved_chunks_count": metrics.get("retrieved_chunks_count", 0),
        "rag_matches_count": metrics.get("rag_matches_count", 0),
        "tool_calls": tool_calls or [],
        "detail": {
            "context_precision_detail": metrics.get("context_precision_detail", {}),
            "faithfulness_detail": metrics.get("faithfulness_detail", {}),
            "answer_relevancy_detail": metrics.get("answer_relevancy_detail", {}),
        },
    }).execute()
    return result.data[0]


def get_rag_evaluations(session_id: str) -> list[dict]:
    """获取一个 session 的所有 RAG 评估记录，用于指标汇总。"""
    db = get_client()
    result = (
        db.table("rag_evaluations")
        .select("*")
        .eq("session_id", session_id)
        .order("turn_number")
        .execute()
    )
    return result.data or []


def save_embedding(
    session_id: str,
    message_id: str,
    embedding: list[float],
    content: str,
    metadata: dict | None = None,
) -> dict:
    db = get_client()
    result = (
        db.table("message_embeddings")
        .insert({
            "session_id": session_id,
            "message_id": message_id,
            "embedding": embedding,
            "content": content,
            "metadata": metadata or {},
        })
        .execute()
    )
    return result.data[0]


def find_similar_embeddings(
    session_id: str,
    query_embedding: list[float],
    threshold: float = 0.75,
    limit: int = 5,
) -> list[dict]:
    db = get_client()
    result = db.rpc(
        "match_session_embeddings",
        {
            "p_session_id": session_id,
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
        },
    ).execute()
    return result.data or []


# Document RAG: resumes and job descriptions

def save_session_resume(
    session_id: str,
    user_id: str,
    content: str,
    source_type: str = "text",
    filename: str | None = None,
    status: str = "processed",
    metadata: dict | None = None,
) -> dict:
    db = get_client()
    payload = {
        "session_id": session_id,
        "user_id": user_id,
        "source_type": source_type,
        "filename": filename,
        "content": content,
        "status": status,
        "metadata": metadata or {},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    # 首次上传时可能没有记录，用 limit(1) 避免 maybe_single 在部分 Supabase 版本里返回 None。
    existing = (
        db.table("session_resumes")
        .select("*")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    existing_rows = existing.data or []
    if existing_rows:
        result = (
            db.table("session_resumes")
            .update(payload)
            .eq("id", existing_rows[0]["id"])
            .execute()
        )
    else:
        result = db.table("session_resumes").insert(payload).execute()
    return result.data[0]


def save_session_job_description(
    session_id: str,
    user_id: str,
    content: str,
    source_type: str = "text",
    filename: str | None = None,
    status: str = "processed",
    metadata: dict | None = None,
) -> dict:
    db = get_client()
    payload = {
        "session_id": session_id,
        "user_id": user_id,
        "source_type": source_type,
        "filename": filename,
        "content": content,
        "status": status,
        "metadata": metadata or {},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    # 首次上传时可能没有记录，用 limit(1) 避免 maybe_single 在部分 Supabase 版本里返回 None。
    existing = (
        db.table("session_job_descriptions")
        .select("*")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    existing_rows = existing.data or []
    if existing_rows:
        result = (
            db.table("session_job_descriptions")
            .update(payload)
            .eq("id", existing_rows[0]["id"])
            .execute()
        )
    else:
        result = db.table("session_job_descriptions").insert(payload).execute()
    return result.data[0]


def delete_document_chunks(
    session_id: str,
    chunk_source: str,
) -> None:
    get_client().table("document_chunks").delete().eq("session_id", session_id).eq(
        "chunk_source",
        chunk_source,
    ).execute()


def save_document_chunk(
    session_id: str,
    chunk_source: str,
    chunk_index: int,
    content: str,
    embedding: list[float],
    resume_id: str | None = None,
    job_description_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    payload = {
        "session_id": session_id,
        "resume_id": resume_id,
        "job_description_id": job_description_id,
        "chunk_source": chunk_source,
        "chunk_index": chunk_index,
        "content": content,
        "embedding": embedding,
        "metadata": metadata or {},
    }
    result = get_client().table("document_chunks").insert(payload).execute()
    return result.data[0]


def find_similar_document_chunks(
    session_id: str,
    query_embedding: list[float],
    threshold: float = 0.72,
    limit: int = 6,
    chunk_source: str | None = None,
) -> list[dict]:
    result = get_client().rpc(
        "match_document_chunks",
        {
            "p_session_id": session_id,
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
            "p_chunk_source": chunk_source,
        },
    ).execute()
    return result.data or []
