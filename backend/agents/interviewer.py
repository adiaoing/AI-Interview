"""
面试官 ReAct Agent。
    让 LLM 自主决定：
    1. 调用哪些工具（搜索简历、JD、历史弱点、长期记忆、能力画像）
    2. 从工具结果中提取关键信息
    3. 结合面试计划生成针对性问题
"""
from __future__ import annotations

import logging
from agents.state import InterviewState
# generate_with_tools：ReAct 式生成
from agents.llm import generate_with_tools, generate_text
from agents.tools import INTERVIEWER_TOOLS, execute_interviewer_tool
from tools.tts import generate_tts

logger = logging.getLogger(__name__)
# 难度映射表
DIFFICULTY_LABELS = {1: "entry-level", 2: "junior", 3: "mid-level", 4: "senior", 5: "staff/principal"}

# ── 系统提示词 ──────────────────────────────────────────────────

REACT_INTERVIEWER_SYSTEM = """
    你是一名专业的中文技术面试官，正在对候选人进行结构化面试。

    【你的核心任务】
    根据当前面试进展，自主决定：
    1. 需要先了解哪些信息（调用工具）
    2. 结合获取的信息，生成最合适的下一个面试问题

    【工具使用原则】
    - 在提问前，你应该主动查阅相关信息，不要凭空出题
    - 如果还没有了解过候选人简历，先调用 search_resume
    - 如果需要围绕岗位要求出题，先调用 search_jd
    - 如果想了解候选人哪些能力还没被测评过，调用 get_competency_profile
    - 如果候选人有反复出现的薄弱点，调用 get_weakness_history 确认是否需要继续追问
    - 可以同时调用多个工具后再决定出什么题

    【提问原则】
    - 每次只问一个问题，不要出复合题
    - 问题要像真人面试官自然发问，不要暴露你的信息来源
    - 不要说"根据你的简历""JD 要求"等显示工具来源的话
    - 基于实际信息提问，不要编造候选人没有的经历
    - 难度要与当前难度等级（{difficulty_label}）匹配

    【面试策略参考】
    {interview_plan}

    【当前面试状态】
    - 目标岗位：{role}
    - 面试类型：{interview_type}
    - 当前难度：{difficulty_label}（{difficulty}/5）
    - 已进行轮次：{turn_count}

    {competency_summary}

    {history_summary}

    请先调用你需要的工具，然后输出一个中文面试问题。
"""

# 把 state 里的能力评分信息整理成 prompt 中的一段文本
def _build_competency_summary(state: InterviewState) -> str:
    scores = state.get("competency_scores", {})
    if not scores:
        return ""
    # 遍历所有能力项，挑出分数小于 3.0 的项，把它们的 key 放进 weak 列表
    weak = [k for k, v in scores.items() if v < 3.0]
    # 挑出分数大于等于 4.0 的能力项，放进 good 列表
    good = [k for k, v in scores.items() if v >= 4.0]
    lines = []
    if weak:
        # 如果 weak 不为空，就拼成一句文本
        lines.append(f"- 薄弱能力项（需重点考查）：{', '.join(weak)}")
    if good:
        lines.append(f"- 表现良好的能力项（可适当减少）：{', '.join(good)}")
    return "【能力评估摘要】\n" + "\n".join(lines) if lines else ""

# 从历史消息里提取“已经问过的问题”，提醒 interviewer 不要重复提问
def _build_history_summary(state: InterviewState) -> str:
    # 从 state 里取全部消息列表，筛选出最近 8 条 interviewer 消息（即面试官提过的问题）
    history = state.get("messages", [])
    interviewer_msgs = [
        m for m in history[-8:] if m.get("role") == "interviewer"
    ]
    if not interviewer_msgs:
        return ""
    lines = [
        f"  Turn {m['turn_number']}: {m['content'][:100]}..."
        if len(m.get("content", "")) > 100
        else f"  Turn {m['turn_number']}: {m.get('content', '')}"
        for m in interviewer_msgs
    ]
    return "【已提问（不要重复）】\n" + "\n".join(lines)

# 把 planner 节点产出的计划整理成 interviewer 可读的摘要
def _build_plan_summary(state: InterviewState) -> str:
    plan = state.get("interview_plan", {})
    if not plan:
        return "（暂无面试计划，请根据实际情况灵活提问）"
    strategy = plan.get("strategy", "")
    competencies = plan.get("key_competencies", [])
    watch_out = plan.get("watch_out", [])
    lines = []
    if strategy:
        lines.append(f"整体策略：{strategy}")
    if competencies:
        lines.append(f"核心能力项：{', '.join(competencies)}")
    # 找当前轮次应该重点考什么
    turn_count = state.get("turn_count", 0)
    sequence = plan.get("question_sequence", [])
    # 在 sequence 里找第一个满足：s.get("turn") == turn_count 的元素
    current_focus = next((s for s in sequence if s.get("turn") == turn_count), None)
    if current_focus:
        # 示例：本轮建议方向：项目经历 — 后端架构设计（原因：验证系统设计能力）
        lines.append(
            f"本轮建议方向：{current_focus.get('focus', '')} — {current_focus.get('topic', '')} "
            f"（原因：{current_focus.get('why', '')}）"
        )
    # 如果有注意事项，也加一行
    if watch_out:
        lines.append(f"注意事项：{'; '.join(watch_out)}")
    return "\n".join(lines)


async def interviewer_node(state: InterviewState) -> dict:
    """
        面试官节点。
        如果当前需要追问，直接使用 followup_question（无需工具调用）。
        否则，启动 ReAct 循环：LLM 自主决定调用工具 → 生成问题。
    """
    # 如果本轮需要追问，直接使用追问问题（followup 节点已经生成好了）
    is_followup = bool(state.get("follow_up_needed") and state.get("follow_up_question"))
    memory_matches: list[dict] = list(state.get("current_user_memory_matches", []))
    tool_calls_log: list[dict] = []

    if is_followup:
        question = state["follow_up_question"]
    else:
        # 算 difficulty_label
        difficulty_label = DIFFICULTY_LABELS.get(state["difficulty"], "mid-level")
        # 构造 prompt
        system = REACT_INTERVIEWER_SYSTEM.format(
            role=state.get("role") or "Software Engineer",
            interview_type=state["interview_type"],
            difficulty_label=difficulty_label,
            difficulty=state["difficulty"],
            turn_count=state.get("turn_count", 0),
            interview_plan=_build_plan_summary(state),
            competency_summary=_build_competency_summary(state),
            history_summary=_build_history_summary(state),
        )

        # 工具执行器（闭包捕获 state）
        async def tool_exec(tool_name: str, tool_args: dict) -> str:
            # 后面 generate_with_tools(...) 在做 ReAct 工具调用时，
            # 不需要自己知道 state 是什么；只要调用 tool_exec，内部就能自动带着当前 state 去执行工具。
            return await execute_interviewer_tool(tool_name, tool_args, state)
        # ReAct 主路径的核心
        # 返回最终生成的问题文本，工具调用日志
        question, tool_calls_log = await generate_with_tools(
            system=system,
            prompt="请先调用你需要的工具了解背景，然后生成下一个面试问题。只输出问题本身，不要输出前言或解释。",
            tools=INTERVIEWER_TOOLS,
            tool_executor=tool_exec,
            max_rounds=4,
            max_tokens=512,
        )

        # 如果 ReAct 没有返回有效问题，fallback 到 generate_text
        if not question or len(question) < 10:
            logger.warning("ReAct returned empty question, falling back to direct generation")
            fallback_system = (
                f"你是一名专业{state['interview_type']}面试官，"
                f"正在面试 {state.get('role', 'Software Engineer')} 候选人。"
                f"难度：{difficulty_label}。请直接输出一个中文面试问题，不要任何前言。"
            )
            question = await generate_text(
                system=fallback_system,
                prompt="生成下一个面试问题",
                max_tokens=256,
            )

    audio = await generate_tts(question, state["session_id"])

    return {
        "current_question": question,
        "current_question_is_followup": is_followup,        # 记录这道题是不是追问
        "current_user_memory_matches": memory_matches,
        "tool_calls_log": tool_calls_log,
        "tts_audio": audio,
        "follow_up_needed": False,
        "follow_up_question": "",
    }
