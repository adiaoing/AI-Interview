'''
    追问节点
        节点的判断依据有两类：
            当前轮的评分结果
            RAG 检索到的历史弱点（如果有的话），尤其是 recurring weakness
'''

from __future__ import annotations
from agents.state import InterviewState
from agents.llm import generate_text
from rag.retriever import find_gaps

FOLLOWUP_SYSTEM = """你是一名中文技术面试官。请基于候选人薄弱或不完整的回答，生成一个具体追问。
追问要聚焦一个明确缺口，帮助候选人补充他刚才漏掉的细节。
Output ONLY the follow-up question text, no preamble."""


async def followup_node(state: InterviewState) -> dict:
    grading = state.get("grading", {})
    score = grading.get("score", 3)
    follow_up_suggestion = grading.get("follow_up_suggestion")
    gaps = grading.get("gaps", [])

    follow_up_needed = False
    follow_up_question = ""

    # 如果候选人刚回答的是追问题，本轮不再继续追问，避免陷入 follow-up 链。
    if state.get("current_question_is_followup"):
        return {
            "follow_up_needed": False,
            "follow_up_question": "",
            "current_rag_matches": [],
            "recurring_weakness_detected": False,
        }

    # 检查 RAG 的重复弱点
    similar = []
    try:
        similar = await find_gaps(
            session_id=state["session_id"],
            current_question=state["current_question"],
            current_answer=state["current_answer"],
        )
    except Exception:
        pass
    # 判断是否存在重复弱点 ：只要当前检索命中的历史相似回答里，存在低分（<3）的记录，就认为当前轮暴露了重复弱点模式
    recurring_weakness = any(
        doc.get("metadata", {}).get("score", 5) < 3
        for doc in similar
    )
    rag_matches = _serialize_rag_matches(similar)
    rag_insights = list(state.get("rag_insights", []))
    if rag_matches:
        # 把本轮命中的历史弱点写回 state，后续 coach/report 不需要重复查库。
        rag_insights.append({
            "turn_number": state.get("turn_count", 0),
            "question": state.get("current_question", ""),
            "recurring_weakness": recurring_weakness,
            "matches": rag_matches,
        })

    # 低分直接追问；中等分数看缺口和历史模式再决定
    should_followup = score <= 2 or (score == 3 and (gaps or recurring_weakness))

    if should_followup:
        follow_up_needed = True
        # 优先使用 grader 已经给出的 follow_up_suggestion
        if follow_up_suggestion:
            follow_up_question = follow_up_suggestion
        else:
            gap_context = ", ".join(gaps) if gaps else "incomplete answer"
            prompt = (
                f"原问题：{state['current_question']}\n"
                f"候选人回答：{state['current_answer']}\n"
                f"识别出的缺口：{gap_context}\n"
                f"目标岗位：{state.get('role', 'Software Engineer')}\n"
                "请只追问一个具体细节，不要连续扩展多个方向。"
            )
            follow_up_question = await generate_text(
                system=FOLLOWUP_SYSTEM,
                prompt=prompt,
                max_tokens=256,
            )

    return {
        "follow_up_needed": follow_up_needed,
        "follow_up_question": follow_up_question,
        "current_rag_matches": rag_matches,
        "recurring_weakness_detected": recurring_weakness,
        "rag_insights": rag_insights,
    }

# 把原始检索结果 similar 压缩成适合写入 state 的结构
def _serialize_rag_matches(similar: list[dict]) -> list[dict]:
    matches: list[dict] = []
    for doc in similar:
        content = doc.get("content", "")
        metadata = doc.get("metadata", {}) or {}
        matches.append({
            "id": str(doc.get("id", "")),
            "content": content[:600],
            "competency": metadata.get("competency"),
            "score": metadata.get("score"),
            "similarity": doc.get("similarity"),
        })
    return matches
