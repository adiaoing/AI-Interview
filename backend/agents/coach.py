"""
    面试教练节点 (Coach Agent with Self-Reflection)。
        新增 self-reflection 循环：
            1. 先生成初稿 coaching note
            2. 用 Critic prompt 检查初稿是否够具体、可执行
            3. 如果检查发现空泛评价，自动修订一次
"""
from __future__ import annotations
import logging
from agents.state import InterviewState
from agents.llm import generate_text

logger = logging.getLogger(__name__)

COACH_SYSTEM = """你是一名中文技术面试教练。请只基于本轮问题、候选人回答和评分信息，给出候选人听得懂、下一轮能立刻改的建议。

输出要求：
- 用中文，最多 3 句话。
- 不要写空泛评价，比如"具备工程落地意识""体现扎实习惯""更凸显量化思维"。
- 必须点名候选人本轮回答里的一个具体内容，再指出缺失的一项具体信息。
- 最后给一句可以直接照着补充的示例表达。
- Output ONLY the coaching note, no preamble."""

# 用来检查初稿
COACH_REFLECTION_SYSTEM = """你是一名教练反馈质检员。请检查以下教练反馈是否符合要求。

检查标准：
1. 是否引用了候选人回答中的具体内容？（不能只说"你的回答"）
2. 是否指出了具体缺失的信息？（不能说"缺乏深度"这类抽象表述）
3. 是否给出了候选人可以直接使用的示例表达？

如果反馈合格，返回: {"verdict": "pass"}
如果不合格，返回: {"verdict": "revise", "issues": ["<问题1>", "<问题2>"], "suggested_revision": "<改进后的反馈（3句以内）>"}

只返回 JSON。"""


async def coach_node(state: InterviewState) -> dict:
    grading = state.get("grading", {})
    score = grading.get("score", 3)
    turn_count = state["turn_count"]
    max_turns = state.get("max_turns", 8)

    coaching_notes = list(state.get("coaching_notes", []))
    # 格式化当前轮 RAG 匹配结果
    rag_context = _format_rag_matches(state.get("current_rag_matches", []))

    # Step 1: 生成初稿 coaching note
    draft_prompt = (
        f"面试问题：{state['current_question']}\n"
        f"候选人回答：{state['current_answer']}\n"
        f"分数：{score}/5\n"
        f"评分反馈：{grading.get('feedback', '')}\n"
        f"优点：{', '.join(grading.get('strengths', []))}\n"
        f"缺口：{', '.join(grading.get('gaps', []))}\n"
        f"历史相似弱点：{rag_context}\n\n"
        "请按这个方向反馈：先说回答里哪个具体点有效，再说缺了什么具体证据或链路，"
        "最后给一句候选人下次可以直接补上的中文表达。"
        "如果存在历史相似弱点，请点明这是重复出现的问题，但不要复述数据库字段。"
    )
    draft = await generate_text(system=COACH_SYSTEM, prompt=draft_prompt, max_tokens=384)

    # Step 2: Self-reflection — 检查初稿质量
    reflection_prompt = (
        f"面试问题：{state['current_question']}\n"
        f"候选人回答片段：{state['current_answer'][:300]}\n\n"
        f"待检查的教练反馈：\n{draft}"
    )
    final_note = draft  # 默认使用初稿
    try:
        import json
        reflection_raw = await generate_text(
            system=COACH_REFLECTION_SYSTEM,
            prompt=reflection_prompt,
            max_tokens=512,
        )
        reflection_raw = reflection_raw.strip()
        if reflection_raw.startswith("```"):
            parts = reflection_raw.split("```")
            reflection_raw = parts[1] if len(parts) > 1 else reflection_raw
            if reflection_raw.startswith("json"):
                reflection_raw = reflection_raw[4:]
        reflection = json.loads(reflection_raw.strip())
        # self-reflection 模型明确判定“需要修改”
        if reflection.get("verdict") == "revise":
            revised = reflection.get("suggested_revision", "").strip()
            if revised and len(revised) > 10:
                final_note = revised
                logger.debug(
                    "Coach self-reflection revised note for session %s",
                    state.get("session_id"),
                )
    except Exception as exc:
        logger.debug("Coach self-reflection parse failed: %s", exc)
        # 解析失败不影响主流程，继续使用初稿

    coaching_notes.append(final_note)

    # 根据能力均值调整难度
    difficulty = state["difficulty"]
    competency_scores = state.get("competency_scores", {})
    if competency_scores:
        avg_score = sum(competency_scores.values()) / len(competency_scores)
        if avg_score >= 4.0 and difficulty < 5:
            difficulty = min(5, difficulty + 1)
        elif avg_score <= 2.0 and difficulty > 1:
            difficulty = max(1, difficulty - 1)

    session_complete = turn_count >= max_turns

    return {
        "coaching_notes": coaching_notes,
        "difficulty": difficulty,
        "session_complete": session_complete,
        "turn_count": turn_count,
    }


def _format_rag_matches(matches: list[dict]) -> str:
    if not matches:
        return "无"

    lines: list[str] = []
    for index, match in enumerate(matches[:3], start=1):
        score = match.get("score")
        competency = match.get("competency") or "未知能力项"
        content = (match.get("content") or "").replace("\n", " ")
        lines.append(f"{index}. 能力项：{competency}，历史分数：{score}，片段：{content[:180]}")
    return "\n".join(lines)
