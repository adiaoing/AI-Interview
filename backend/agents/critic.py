"""
    评分质检节点 (Critic Agent)。

    在 grader_node 之后、followup_node 之前运行。
    
    使用 Self-Reflection 模式对 grader 的输出进行验证和纠正：
    1. 验证能力项标签是否与题目内容匹配
    2. 验证分数与评语是否自洽（gaps 多 → 分数应低）
    3. 检查 feedback 是否足够具体（拒绝空泛评语）
    4. 如有问题，自动修正输出

    critic_node 不会大幅改变分数，只做小范围校正（±1分）。
"""
from __future__ import annotations

import json
import logging

from agents.state import InterviewState
from agents.llm import generate_text

logger = logging.getLogger(__name__)

CRITIC_SYSTEM = """你是一名面试评分质检官。你的任务是审核 grader 的评分结果，确保评分客观准确。

【检查维度】
1. competency 与题目内容是否匹配（题目考察什么能力，标签是否准确）
2. score 与 gaps/strengths 是否自洽：
   - gaps 有 2 个以上 → score 不应高于 3
   - strengths 有 2 个以上且 gaps 为空 → score 不应低于 4
   - score 为 1 但有实质性回答 → 可能偏低
3. feedback 是否引用了候选人回答中的具体内容（拒绝"具有工程思维""体现扎实基础"等空泛评语）
4. follow_up_suggestion 是否具体可执行（如果 score ≤ 3 但没有 follow_up_suggestion，应补充）

【返回规则】
- 如果评分基本正确（score 偏差在 ±1 以内），直接返回 {"verdict": "pass", "corrections": {}}
- 如果需要修正，返回 {"verdict": "corrected", "corrections": {<需要修改的字段>: <新值>}, "reason": "<一句中文说明>"}

只返回 JSON，不要输出其他内容。"""


async def critic_node(state: InterviewState) -> dict:
    """验证并修正 grader 的评分结果。"""
    grading = state.get("grading", {})
    if not grading:
        return {}  # 没有评分结果，跳过

    question = state.get("current_question", "")
    answer = state.get("current_answer", "")

    prompt = (
        f"面试问题：{question}\n\n"
        f"候选人回答：{answer[:800]}\n\n"
        f"Grader 输出：\n"
        f"  score: {grading.get('score')}\n"
        f"  competency: {grading.get('competency')}\n"
        f"  feedback: {grading.get('feedback')}\n"
        f"  strengths: {grading.get('strengths', [])}\n"
        f"  gaps: {grading.get('gaps', [])}\n"
        f"  follow_up_suggestion: {grading.get('follow_up_suggestion')}"
    )

    try:
        raw = await generate_text(system=CRITIC_SYSTEM, prompt=prompt, max_tokens=512)
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
    except Exception as exc:
        logger.warning("Critic node failed to parse: %s", exc)
        return {}  # 解析失败，保留原始 grading

    verdict = result.get("verdict", "pass")
    corrections = result.get("corrections", {})

    if verdict == "pass" or not corrections:
        logger.debug("Critic: grading passed validation")
        return {}  # 评分通过，无需修改

    # 如果需要修正，先复制原 grading
    corrected_grading = dict(grading)
    corrected_grading.update(corrections)

    # 限制分数修正范围（不超过原分 ±1）
    original_score = grading.get("score", 3)
    new_score = corrected_grading.get("score", original_score)
    corrected_grading["score"] = max(
        original_score - 1,
        min(original_score + 1, new_score),
    )

    reason = result.get("reason", "")
    logger.info(
        "Critic corrected grading for session %s: score %s→%s | reason: %s",
        state.get("session_id"),
        original_score,
        corrected_grading["score"],
        reason,
    )

    # 如果分数变化了，同步更新 competency_scores
    updated_scores = dict(state.get("competency_scores", {}))
    competency = corrected_grading.get("competency", "general")
    if corrected_grading["score"] != original_score and competency in updated_scores:
        # 重新计算滚动均值（简单调整）
        prev = updated_scores[competency]
        updated_scores[competency] = (prev + corrected_grading["score"]) / 2

    return {
        "grading": corrected_grading,
        "competency_scores": updated_scores,
    }
