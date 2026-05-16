"""RAG 评估模块 — LLM-as-Judge 实现四项核心指标。

指标说明：
    - context_precision:  召回的上下文中，真正被 LLM 使用生成问题的比例 (0-1)
    - faithfulness:       生成的问题是否忠于检索上下文，没有幻觉 (0-1)
    - answer_relevancy:   候选人回答与面试问题的相关程度 (0-1)
    - weakness_detection: 当分数 ≤ 2 时 RAG 是否成功检测到历史薄弱点 (precision)
"""
from __future__ import annotations

import json
import logging
from agents.llm import generate_text

logger = logging.getLogger(__name__)

# ── Evaluation prompts ─────────────────────────────────────────────────────────

_CONTEXT_PRECISION_SYSTEM = """你是一名 RAG 检索质量评估员。
给定"检索到的上下文片段列表"和"基于这些片段生成的面试问题"，
判断每个片段是否实质性地影响了问题的生成（即被使用了）。

返回 JSON，格式如下（不要输出其他内容）：
{
  "used_chunk_indices": [<被使用的片段序号列表，从 0 开始>],
  "precision": <0.0-1.0 的小数，= 被使用片段数 / 总片段数>,
  "reasoning": "<一句中文说明>"
}"""

_FAITHFULNESS_SYSTEM = """你是一名 RAG 可信度评估员。
给定"检索到的上下文片段"和"基于这些片段生成的面试问题"，
判断问题内容是否完全基于上下文（忠实），还是包含了上下文之外的编造信息。

返回 JSON（不要输出其他内容）：
{
  "score": <0.0-1.0，1.0=完全忠实，0.0=完全幻觉>,
  "hallucinated_claims": ["<编造的信息1>", ...],
  "reasoning": "<一句中文说明>"
}"""

_ANSWER_RELEVANCY_SYSTEM = """你是一名面试质量评估员。
给定"面试问题"和"候选人回答"，评估回答与问题的相关程度。
注意：只评估相关性，不评估质量高低。

返回 JSON（不要输出其他内容）：
{
  "score": <0.0-1.0，1.0=完全相关，0.0=完全跑题>,
  "on_topic_elements": ["<相关点1>", ...],
  "off_topic_elements": ["<跑题点1>", ...],
  "reasoning": "<一句中文说明>"
}"""


# ── Individual metric functions ────────────────────────────────────────────────

async def evaluate_context_precision(
    retrieved_chunks: list[str],
    generated_question: str,
) -> dict:
    """计算 Context Precision：检索片段中实际被使用的比例。"""
    if not retrieved_chunks or not generated_question:
        return {"precision": 0.0, "reasoning": "无检索片段或问题为空", "used_chunk_indices": []}

    chunks_text = "\n".join(
        f"[片段 {i}]: {chunk[:400]}" for i, chunk in enumerate(retrieved_chunks)
    )
    prompt = (
        f"检索到的上下文片段：\n{chunks_text}\n\n"
        f"生成的面试问题：{generated_question}"
    )
    try:
        raw = await generate_text(system=_CONTEXT_PRECISION_SYSTEM, prompt=prompt, max_tokens=512)
        raw = _strip_fences(raw)
        result = json.loads(raw)
        return {
            "precision": float(result.get("precision", 0.0)),
            "used_chunk_indices": result.get("used_chunk_indices", []),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as exc:
        logger.warning("context_precision eval failed: %s", exc)
        return {"precision": 0.0, "reasoning": f"评估失败: {exc}", "used_chunk_indices": []}


async def evaluate_faithfulness(
    generated_question: str,
    retrieved_chunks: list[str],
) -> dict:
    """计算 Faithfulness：问题内容是否忠于检索上下文。"""
    if not retrieved_chunks or not generated_question:
        return {"score": 1.0, "reasoning": "无检索片段，无法判断幻觉", "hallucinated_claims": []}

    context = "\n".join(f"[片段 {i}]: {c[:400]}" for i, c in enumerate(retrieved_chunks))
    prompt = (
        f"检索到的上下文：\n{context}\n\n"
        f"生成的面试问题：{generated_question}"
    )
    try:
        raw = await generate_text(system=_FAITHFULNESS_SYSTEM, prompt=prompt, max_tokens=512)
        raw = _strip_fences(raw)
        result = json.loads(raw)
        return {
            "score": float(result.get("score", 1.0)),
            "hallucinated_claims": result.get("hallucinated_claims", []),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as exc:
        logger.warning("faithfulness eval failed: %s", exc)
        return {"score": 1.0, "reasoning": f"评估失败: {exc}", "hallucinated_claims": []}


async def evaluate_answer_relevancy(
    question: str,
    answer: str,
) -> dict:
    """计算 Answer Relevancy：候选人回答与问题的相关程度。"""
    if not question or not answer:
        return {"score": 0.0, "reasoning": "问题或回答为空", "on_topic_elements": [], "off_topic_elements": []}

    prompt = f"面试问题：{question}\n\n候选人回答：{answer[:1500]}"
    try:
        raw = await generate_text(system=_ANSWER_RELEVANCY_SYSTEM, prompt=prompt, max_tokens=512)
        raw = _strip_fences(raw)
        result = json.loads(raw)
        return {
            "score": float(result.get("score", 0.0)),
            "on_topic_elements": result.get("on_topic_elements", []),
            "off_topic_elements": result.get("off_topic_elements", []),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as exc:
        logger.warning("answer_relevancy eval failed: %s", exc)
        return {"score": 0.0, "reasoning": f"评估失败: {exc}", "on_topic_elements": [], "off_topic_elements": []}


def evaluate_weakness_detection(
    rag_matches: list[dict],
    actual_score: int,
) -> dict:
    """计算弱点检测精准度（无需 LLM，规则判断）。

    逻辑：
    - 如果 actual_score <= 2（真弱），RAG 有命中 → TP（正确预警）
    - 如果 actual_score <= 2（真弱），RAG 无命中 → FN（漏检）
    - 如果 actual_score >= 4（表现好），RAG 有命中 → FP（误报）
    - 如果 actual_score >= 4（表现好），RAG 无命中 → TN（正确无报）
    """
    has_matches = bool(rag_matches)
    is_weak = actual_score <= 2
    # 真实很弱，而且 RAG 命中了
    if is_weak and has_matches:
        outcome = "TP"
        correct = True
    # 真实很弱，但 RAG 没命中
    elif is_weak and not has_matches:
        outcome = "FN"
        correct = False
    # 真实表现好，但 RAG 命中了
    elif not is_weak and has_matches:
        outcome = "FP"
        correct = False
    # 真实表现好，且 RAG 没命中
    else:
        outcome = "TN"
        correct = True

    return {
        "outcome": outcome,
        "correct": correct,
        "actual_score": actual_score,
        "rag_matched": has_matches,
        "match_count": len(rag_matches),
    }


# ── Composite runner ───────────────────────────────────────────────────────────

async def run_turn_evaluation(
    question: str,
    answer: str,
    generated_next_question: str,
    retrieved_chunks: list[str],
    rag_matches: list[dict],
    actual_score: int,
) -> dict:
    """为一个完整的 turn 运行所有 RAG 评估指标，返回汇总结果。

    此函数应在 index_answer_node 中异步调用，不阻断主流程。
    """
    # 指标关注的是：RAG 检索出来的上下文，有没有被拿去生成下一题
    cp_result = await evaluate_context_precision(retrieved_chunks, generated_next_question)
    faith_result = await evaluate_faithfulness(generated_next_question, retrieved_chunks)
    # 围绕当前问题和当前回答的关系
    ar_result = await evaluate_answer_relevancy(question, answer)
    wd_result = evaluate_weakness_detection(rag_matches, actual_score)

    return {
        "context_precision": cp_result["precision"],
        "context_precision_detail": cp_result,
        "faithfulness": faith_result["score"],
        "faithfulness_detail": faith_result,
        "answer_relevancy": ar_result["score"],
        "answer_relevancy_detail": ar_result,
        "weakness_detection": wd_result,
        # Aggregate summary score (0-1)
        "aggregate_score": round(
            (cp_result["precision"] + faith_result["score"] + ar_result["score"]) / 3, 3
        ),
        "retrieved_chunks_count": len(retrieved_chunks),
        "rag_matches_count": len(rag_matches),
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _strip_fences(raw: str) -> str:
    """去掉 Markdown 代码块围栏"""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()
