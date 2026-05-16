"""
    面试策略规划节点 (Planner Agent)。

    在面试开始前（或需要重新规划时）调用，生成结构化的面试计划：
        - 分析岗位要求和候选人背景
        - 确定重点考查的能力维度
        - 规划问题序列和深度分布
        - 记录需要关注的风险点

    规划器使用 LLM-as-Planner 模式：一次性生成完整计划，
    不使用工具调用（因为此时面试还没开始，简历/JD 由 retrieve_interview_document_context 统一获取）。
"""
from __future__ import annotations

import json
import logging

from agents.state import InterviewState
from agents.llm import generate_text

logger = logging.getLogger(__name__)

PLANNER_SYSTEM = """你是一名资深技术面试策略规划专家。

根据提供的岗位信息、候选人背景和面试配置，生成一份结构化面试计划。

返回 JSON（严格按照以下格式，不要输出其他内容）：
{
  "strategy": "<整体面试策略，2-3句话，说明你打算如何分配提问重心>",
  "key_competencies": ["<能力项1>", "<能力项2>", "<能力项3>", "<能力项4>"],
  "question_sequence": [
    {"turn": 0, "focus": "<聚焦方向>", "topic": "<具体话题>", "why": "<原因>"},
    {"turn": 1, "focus": "<聚焦方向>", "topic": "<具体话题>", "why": "<原因>"},
    {"turn": 2, "focus": "<聚焦方向>", "topic": "<具体话题>", "why": "<原因>"},
    {"turn": 3, "focus": "<聚焦方向>", "topic": "<具体话题>", "why": "<原因>"}
  ],
  "watch_out": ["<风险点或需要特别关注的地方1>", "<风险点2>"]
}

focus 可选值：
- resume_deep_dive：深挖简历项目细节
- technical_foundation：技术基础知识考察
- project_decision：项目中的技术决策与取舍
- scenario_problem：岗位场景题
- behavioral：行为面试题（STAR格式）
- system_design：系统设计
- cross_cutting：沟通协作、复盘、质量意识等综合能力

注意：question_sequence 只需规划前 4 轮，面试官会根据实际情况灵活调整后续问题。"""

# index_answer 之后的路由函数会调用它，决定要不要回到 planner 节点
def _should_replan(state: InterviewState) -> bool:
    """
        判断是否需要重新规划。
            没有计划 → 要规划
            有计划但距上次规划不到 4 轮 → 不重规划
            够 4 轮了，再看能力项
                如果至少有 2 个能力项平均分 < 2.5 → 重规划
                否则不重规划。
    """
    plan = state.get("interview_plan")
    if not plan:
        return True  # 还没有计划
    # 每 4 轮检查一次是否需要根据能力评估结果更新计划
    turn_count = state.get("turn_count", 0)
    plan_turn = state.get("plan_updated_at", 0)
    if turn_count - plan_turn < 4:
        return False  # 距上次规划不足 4 轮，不重新规划
    # 如果有某个能力项持续薄弱（平均分 < 2.5），触发重新规划
    scores = state.get("competency_scores", {})
    weak_count = sum(1 for s in scores.values() if s < 2.5)
    return weak_count >= 2


async def planner_node(state: InterviewState) -> dict:
    """
        生成或更新面试计划。
        - 首次调用（turn_count == 0）：生成完整计划
        - 后续调用（来自 index_answer 的重新规划路由）：基于当前能力评估更新计划
    """
    if not _should_replan(state):
        return {}

    turn_count = state.get("turn_count", 0)
    role = state.get("role") or "Software Engineer"
    interview_type = state.get("interview_type", "general")
    difficulty = state.get("difficulty", 3)
    max_turns = state.get("max_turns", 8)

    # 尝试获取文档上下文（简历 + JD 摘要）
    doc_context = ""
    try:
        from rag.documents import retrieve_interview_document_context
        result = await retrieve_interview_document_context(
            session_id=state["session_id"],
            query=f"{role} {interview_type} interview key skills competencies",
            threshold=0.0,
            resume_limit=4,
            jd_limit=3,
            max_context_chars=3000,
        )
        doc_context = result.get("context", "")
    except Exception as exc:
        logger.warning("Planner failed to get doc context: %s", exc)

    # 如果没有文档，尝试用户长期记忆
    memory_context = ""
    if not doc_context:
        try:
            from rag.user_memories import retrieve_user_memory_context
            result = await retrieve_user_memory_context(
                user_id=state["user_id"],
                query=f"{role} technical background project experience",
                threshold=0.65,
                limit=4,
            )
            memory_context = result.get("context", "")
        except Exception:
            pass

    # 构建规划 prompt
    prompt_parts = [
        f"目标岗位：{role}",
        f"面试类型：{interview_type}",
        f"难度等级：{difficulty}/5",
        f"计划面试轮数：{max_turns}",
    ]

    if turn_count > 0:
        # 重新规划：加入当前评估情况
        scores = state.get("competency_scores", {})
        if scores:
            # 如果有 scores，就把它们格式化进 prompt
            # 把每个能力项格式化成一行：- xxx: 3.5/5
            # 把这些行拼成一整段，append 到 prompt_parts。
            score_lines = [f"  - {k}: {v:.1f}/5" for k, v in sorted(scores.items())]
            prompt_parts.append("当前能力评估结果（已测评）：\n" + "\n".join(score_lines))
        # 拿当前累计的 RAG 洞察
        rag_insights = state.get("rag_insights", [])
        # 保留那些被标记为重复弱点的历史记录
        weak_insights = [i for i in rag_insights if i.get("recurring_weakness")]
        if weak_insights:
            prompt_parts.append(f"反复薄弱点轮次数：{len(weak_insights)}（需要调整策略）")
        prompt_parts.append(f"当前已完成轮次：{turn_count}，剩余约 {max_turns - turn_count} 轮")

    if doc_context:
        prompt_parts.append(f"\n候选人简历和岗位 JD 摘要：\n{doc_context}")
    elif memory_context:
        prompt_parts.append(f"\n候选人历史记忆：\n{memory_context}")
    else:
        prompt_parts.append("\n（未上传简历或 JD，请根据岗位通用要求规划）")

    prompt = "\n".join(prompt_parts) + "\n\n请生成面试计划。"

    raw = await generate_text(system=PLANNER_SYSTEM, prompt=prompt, max_tokens=1024)

    # 解析 JSON 计划
    plan: dict = {}
    try:
        raw_clean = raw.strip()
        if raw_clean.startswith("```"):
            parts = raw_clean.split("```")
            raw_clean = parts[1] if len(parts) > 1 else raw_clean
            if raw_clean.startswith("json"):
                raw_clean = raw_clean[4:]
        plan = json.loads(raw_clean.strip())
    except Exception as exc:
        logger.warning("Failed to parse planner output: %s | raw: %s", exc, raw[:200])
        # 降级：创建一个通用计划
        plan = {
            "strategy": f"围绕{role}岗位核心能力进行结构化考察，从项目经历切入，逐步深入技术原理。",
            "key_competencies": ["技术深度", "项目经验", "问题解决", "沟通表达"],
            "question_sequence": [
                {"turn": 0, "focus": "resume_deep_dive", "topic": "核心项目介绍", "why": "建立基础认知"},
                {"turn": 1, "focus": "technical_foundation", "topic": "技术原理", "why": "验证理论基础"},
                {"turn": 2, "focus": "project_decision", "topic": "技术决策", "why": "考察深度思考"},
                {"turn": 3, "focus": "scenario_problem", "topic": "岗位场景", "why": "评估实战能力"},
            ],
            "watch_out": ["注意候选人是否只会背概念而无实践经验"],
        }

    logger.info(
        "Planner generated plan for session %s (turn=%d): competencies=%s",
        state["session_id"],
        turn_count,
        plan.get("key_competencies", []),
    )

    return {
        "interview_plan": plan,
        "plan_updated_at": turn_count,
    }
