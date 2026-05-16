"""
    Interviewer Agent 可调用的工具集。
    每个工具对应一个 async 执行函数，供 ReAct 循环调用。
    工具 schema 使用 OpenAI function-calling 格式（DashScope 兼容）。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.state import InterviewState

logger = logging.getLogger(__name__)


'''
    interviewer ReAct agent “看得见的工具清单”
        "search_resume" : 搜索简历
        "search_jd" : 搜索岗位 JD
        "get_competency_profile" : 获取能力画像
        "get_weakness_history" : 获取历史弱点记录
        "get_user_long_term_memories" : 获取用户长期记忆
'''
INTERVIEWER_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_resume",
            "description": (
                "语义搜索候选人简历中的相关内容。"
                "用于了解候选人的项目经历、技术栈、职责和成就，从而提出有针对性的面试问题。"
                "如果需要围绕候选人具体项目发问，必须先调用此工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询，描述你想了解的候选人信息，例如：'机器学习项目经验' 或 'Python 后端开发经历'",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_jd",
            "description": (
                "语义搜索岗位 JD 中的核心技能要求和岗位职责。"
                "用于了解岗位期望，提出与实际工作相关的技术或场景问题。"
                "如果需要提问岗位基础知识或场景题，必须先调用此工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询，例如：'数据处理能力要求' 或 '系统设计经验'",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_competency_profile",
            "description": (
                "获取候选人当前各能力维度的得分和评估次数。"
                "用于了解哪些能力已经测评、哪些还未覆盖，以及候选人的薄弱能力项，"
                "从而决定下一题是补充薄弱项还是探索新能力维度。"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weakness_history",
            "description": (
                "查询候选人在本次面试中反复暴露的薄弱点记录。"
                "用于判断是否需要继续追问某个方向，或者已经收集了足够证据。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回最近 N 条薄弱点记录，默认 3",
                        "default": 3,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_long_term_memories",
            "description": (
                "查询候选人跨会话的长期记忆，包括技能背景、历史项目、优势和偏好。"
                "当没有上传简历或 JD 时，这是主要的候选人背景信息来源。"
                "也可与简历一起使用，补充历史面试中发现的模式。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询，描述你想了解的候选人历史信息",
                    },
                    "memory_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "过滤记忆类型：profile（背景）, project（项目）, strength（优势）, weakness（弱点）, preference（偏好）。不填则搜索全部类型。",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# ── 工具执行函数 ──────────────────────────────────────────────────────────────

async def execute_interviewer_tool(
    tool_name: str,
    tool_args: dict,
    state: "InterviewState",
) -> str:
    """执行面试官 ReAct agent 的工具调用，返回字符串结果。"""
    # 延迟导入，避免循环依赖
    from rag.documents import retrieve_interview_document_context
    from rag.user_memories import retrieve_user_memory_context

    if tool_name == "search_resume":
        # 从工具参数里拿 query
        query = tool_args.get("query", "")
        try:
            result = await retrieve_interview_document_context(
                session_id=state["session_id"],
                query=query,
                threshold=0.0,
                resume_limit=5,
                jd_limit=0,
                max_context_chars=3000,
            )
            context = result.get("context", "")
            return context if context else "未找到相关简历内容，可能尚未上传简历。"
        except Exception as exc:
            logger.warning("search_resume tool failed: %s", exc)
            return f"简历搜索失败：{exc}"

    elif tool_name == "search_jd":
        query = tool_args.get("query", "")
        try:
            result = await retrieve_interview_document_context(
                session_id=state["session_id"],
                query=query,
                threshold=0.0,
                resume_limit=0,
                jd_limit=5,
                max_context_chars=3000,
            )
            context = result.get("context", "")
            return context if context else "未找到相关 JD 内容，可能尚未上传岗位描述。"
        except Exception as exc:
            logger.warning("search_jd tool failed: %s", exc)
            return f"JD 搜索失败：{exc}"

    elif tool_name == "get_competency_profile":
        scores = state.get("competency_scores", {})
        if not scores:
            return "当前尚无能力评估记录，这是第一轮提问。"
        lines = []
        # 得到 (能力项, 分数) 对，并按分数从低到高排序
        for comp, score in sorted(scores.items(), key=lambda x: x[1]):
            label = _score_label(score)
            # 生成类似这样的文本：system_design：2.5/5.0（一般）
            lines.append(f"  • {comp}：{score:.1f}/5.0（{label}）")
        # 看面试计划里还有哪些能力项尚未覆盖
        plan = state.get("interview_plan", {})
        planned = set(plan.get("key_competencies", []))
        covered = set(scores.keys())
        uncovered = planned - covered
        result = "【已评估能力项】\n" + "\n".join(lines)
        if uncovered:
            result += f"\n\n【计划中尚未覆盖的能力项】：{', '.join(uncovered)}"
        return result

    elif tool_name == "get_weakness_history":
        limit = tool_args.get("limit", 3)
        rag_insights = state.get("rag_insights", [])
        if not rag_insights:
            return "本次面试暂无历史薄弱点记录。"
        weak_insights = [i for i in rag_insights if i.get("recurring_weakness")]
        recent = weak_insights[-limit:] if weak_insights else []
        if not recent:
            return "本次面试暂未检测到反复出现的薄弱点。"
        lines = []
        for insight in recent:
            q_preview = (insight.get("question") or "")[:80]
            lines.append(f"  • Turn {insight['turn_number']}：{q_preview}")
        return "【反复出现的薄弱点】\n" + "\n".join(lines)

    elif tool_name == "get_user_long_term_memories":
        query = tool_args.get("query", "")
        memory_types = tool_args.get("memory_types") or None
        try:
            result = await retrieve_user_memory_context(
                user_id=state["user_id"],
                query=query,
                threshold=0.65,
                limit=4,
                memory_types=memory_types,
            )
            context = result.get("context", "")
            return context if context else "未找到相关历史记忆。"
        except Exception as exc:
            logger.warning("get_user_long_term_memories tool failed: %s", exc)
            return f"记忆检索失败：{exc}"

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


def _score_label(score: float) -> str:
    if score >= 4.5:
        return "优秀"
    if score >= 3.5:
        return "良好"
    if score >= 2.5:
        return "一般"
    if score >= 1.5:
        return "较弱"
    return "薄弱"
