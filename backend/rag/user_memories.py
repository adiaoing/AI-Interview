from __future__ import annotations

import json

from agents.llm import generate_text
from db.queries import find_similar_user_memories, save_user_memory, touch_user_memories
from rag.embeddings import embed_text

MEMORY_TYPES = {"profile", "project", "strength", "weakness", "preference"}

TURN_MEMORY_SYSTEM = """你是候选人长期记忆抽取器。
你的任务是从单轮面试问答中，只提取适合跨 session 保存的稳定信息。

Return ONLY valid JSON array. Each item must follow:
{
  "memory_type": "profile|project|strength|weakness|preference",
  "content": "<one concise Chinese sentence>",
  "confidence": <float 0-1>
}

抽取规则：
- 只保留跨 session 仍然有价值的稳定信息。
- 不要记录一次性的答案细节、原题题干、瞬时情绪、临时表述或原始分数。
- profile：长期技能栈、经验方向、背景标签。
- project：稳定的项目背景、职责范围、关键技术栈。
- strength：比较稳定的优势，不要写空泛表扬。
- weakness：只有当弱点明显结构化，或本轮已体现为重复问题时才写。
- preference：候选人偏好的岗位方向、技术方向、工作重心。
- content 必须独立可读，直接以“候选人...”开头，不要用代词。
- 如果没有足够稳定的信息，返回 []。
- 最多返回 3 条。"""

RESUME_MEMORY_SYSTEM = """你是候选人长期记忆抽取器。
请从简历中提取适合跨 session 保存的稳定信息。

Return ONLY valid JSON array. Each item must follow:
{
  "memory_type": "profile|project|strength|preference",
  "content": "<one concise Chinese sentence>",
  "confidence": <float 0-1>
}

抽取规则：
- 优先抽取长期技能栈、核心项目背景、显著优势、目标岗位方向。
- 不要照抄整段简历；每条都要压缩成一句可复用的陈述。
- content 必须以“候选人...”开头。
- 如果简历信息不充分，返回 []。
- 最多返回 4 条。"""


async def index_turn_user_memories(
    *,
    user_id: str,
    session_id: str,
    role: str | None,
    question: str,
    answer: str,
    grading: dict,
    recurring_weakness_detected: bool = False,
) -> list[dict]:
    prompt = (
        f"目标岗位：{role or 'Software Engineer'}\n"
        f"面试问题：{question}\n"
        f"候选人回答：{answer}\n"
        f"评分反馈：{grading.get('feedback', '')}\n"
        f"识别到的优点：{', '.join(grading.get('strengths', []))}\n"
        f"识别到的缺口：{', '.join(grading.get('gaps', []))}\n"
        f"是否命中重复弱点：{'是' if recurring_weakness_detected else '否'}\n"
    )
    memories = await _extract_memories(
        system=TURN_MEMORY_SYSTEM,
        prompt=prompt,
        allowed_types=MEMORY_TYPES,
        min_confidence=0.78,
        max_items=3,
    )
    return await _persist_memories(
        user_id=user_id,
        session_id=session_id,
        memories=memories,
    )


async def index_resume_user_memories(
    *,
    user_id: str,
    session_id: str,
    role: str | None,
    resume_content: str,
) -> list[dict]:
    prompt = (
        f"目标岗位：{role or 'Software Engineer'}\n"
        f"简历内容：\n{resume_content[:6000]}"
    )
    memories = await _extract_memories(
        system=RESUME_MEMORY_SYSTEM,
        prompt=prompt,
        allowed_types={"profile", "project", "strength", "preference"},
        min_confidence=0.82,
        max_items=4,
    )
    return await _persist_memories(
        user_id=user_id,
        session_id=session_id,
        memories=memories,
    )


async def retrieve_user_memory_context(
    *,
    user_id: str,
    query: str,
    threshold: float = 0.68,
    limit: int = 4,
    memory_types: list[str] | None = None,
    max_chars: int = 1800,
) -> dict:
    normalized_query = (query or "").strip()
    if not normalized_query:
        return {"memories": [], "context": ""}

    query_embedding = await embed_text(normalized_query)
    matches = find_similar_user_memories(
        user_id=user_id,
        query_embedding=query_embedding,
        threshold=threshold,
        limit=limit,
        memory_types=memory_types,
    )
    serialized = _serialize_memory_matches(matches)
    touch_user_memories([item["id"] for item in serialized if item.get("id")])

    return {
        "memories": serialized,
        "context": format_user_memory_context(serialized, max_chars=max_chars),
    }


def format_user_memory_context(memories: list[dict], max_chars: int = 1800) -> str:
    if not memories:
        return ""

    lines = ["候选人跨 session 长期记忆："]
    for index, memory in enumerate(memories, start=1):
        confidence = memory.get("confidence")
        similarity = memory.get("similarity")
        detail = []
        if isinstance(confidence, (int, float)):
            detail.append(f"confidence={confidence:.2f}")
        if isinstance(similarity, (int, float)):
            detail.append(f"similarity={similarity:.2f}")
        suffix = f" ({', '.join(detail)})" if detail else ""
        lines.append(
            f"{index}. [{memory.get('memory_type', 'profile')}] {memory.get('content', '')}{suffix}"
        )

    context = "\n".join(lines)
    if len(context) <= max_chars:
        return context
    return context[:max_chars].rstrip() + "\n..."


async def _extract_memories(
    *,
    system: str,
    prompt: str,
    allowed_types: set[str],
    min_confidence: float,
    max_items: int,
) -> list[dict]:
    raw = await generate_text(system=system, prompt=prompt, max_tokens=900)
    payload = _parse_json_array(raw)
    results: list[dict] = []

    for item in payload:
        memory_type = str(item.get("memory_type", "")).strip()
        content = _normalize_memory_content(str(item.get("content", "")))
        confidence = _to_confidence(item.get("confidence"))
        if (
            memory_type not in allowed_types
            or not content
            or len(content) < 8
            or confidence < min_confidence
        ):
            continue
        results.append({
            "memory_type": memory_type,
            "content": content,
            "confidence": confidence,
        })
        if len(results) >= max_items:
            break

    return results


async def _persist_memories(
    *,
    user_id: str,
    session_id: str,
    memories: list[dict],
) -> list[dict]:
    saved: list[dict] = []
    for memory in memories:
        embedding = await embed_text(f"{memory['memory_type']}: {memory['content']}")
        saved.append(
            save_user_memory(
                user_id=user_id,
                memory_type=memory["memory_type"],
                content=memory["content"],
                embedding=embedding,
                source_session_id=session_id,
                confidence=memory["confidence"],
            )
        )
    return saved


def _serialize_memory_matches(matches: list[dict]) -> list[dict]:
    serialized: list[dict] = []
    for match in matches:
        serialized.append({
            "id": str(match.get("id", "")),
            "memory_type": match.get("memory_type"),
            "content": match.get("content", ""),
            "confidence": float(match["confidence"]) if match.get("confidence") is not None else None,
            "source_session_id": str(match["source_session_id"]) if match.get("source_session_id") else None,
            "last_used_at": match.get("last_used_at"),
            "similarity": match.get("similarity"),
        })
    return serialized


def _parse_json_array(raw: str) -> list[dict]:
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    data = json.loads(cleaned.strip())
    return data if isinstance(data, list) else []


def _normalize_memory_content(content: str) -> str:
    normalized = " ".join(content.replace("\n", " ").split()).strip()
    if not normalized:
        return ""
    if not normalized.startswith("候选人"):
        normalized = f"候选人{normalized}"
    return normalized


def _to_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))
