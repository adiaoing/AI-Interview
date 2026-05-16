"""
    定义整张图的节点、边、路由和中断点
        用 MemorySaver 做检查点
        用 interrupt_before=["grader"] 做中断
        index_answer 这个节点会做 RAG 评估和写库
        流程图：
            [START] → planner → interviewer → [INTERRUPT before grader]
            → grader → critic → followup → coach → index_answer
            → [should_continue_or_replan]
"""
from __future__ import annotations

import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agents.state import InterviewState
from agents.interviewer import interviewer_node         # 出题节点
from agents.grader import grader_node                   # 评分节点
from agents.critic import critic_node                   # 评分校验节点
from agents.followup import followup_node               # 追问节点
from agents.coach import coach_node                     # 教练建议节点
from agents.planner import planner_node, _should_replan # 规划节点，放在图入口；当前是不是该重新规划
from rag.retriever import index_answer                  # 函数：把当前问答写到 session 级 RAG 里
from rag.user_memories import index_turn_user_memories  # 函数：从当前这一轮问答中提取跨 session 的用户记忆

logger = logging.getLogger(__name__)

# ── index_answer + RAG eval node ───────────────────────────────────────────────

async def index_answer_node(state: InterviewState) -> dict:
    """
        这个节点做三件事：
            1. 把当前问答写到 session 级 RAG 里（供后续弱点检测用）
            2. 从当前这一轮问答中提取跨 session 的用户记忆（供后续个性化面试计划用）
            3. 跑 RAG 评估
    """
    message_id = state.get("current_message_id")
    if not message_id:
        return {}
    # 从 state 里取当前轮评分结果
    grading = state.get("grading", {})

    # 1. 写入 session-level RAG（用于弱点检测）
    try:
        await index_answer(
            session_id=state["session_id"],                     # 会话senssion id
            message_id=message_id,                              # 这条用户回答的数据库 id
            question=state["current_question"],                 # 当前问题文本
            answer=state["current_answer"],                     # 当前回答文本
            competency=grading.get("competency", "general"),    # 当前回答对应的能力维度标签
            score=grading.get("score", 3),                      # 当前回答的分数（默认为 3 分，表示中等水平）
        )
    except Exception as exc:
        logger.warning("index_answer failed: %s", exc)

    # 2. 提取跨会话用户记忆
    try:
        await index_turn_user_memories(
            user_id=state["user_id"],                                                   # 谁的长期记忆,用户维度
            session_id=state["session_id"],                                             # 这条记忆来自哪一场 session
            role=state.get("role"),                                                     # 当前面试目标岗位
            question=state["current_question"],                                         # 当前问题文本
            answer=state["current_answer"],                                             # 当前回答文本
            grading=grading,
            recurring_weakness_detected=bool(state.get("recurring_weakness_detected")), # 是否检测到重复弱点
        )
    except Exception as exc:
        logger.warning("index_turn_user_memories failed: %s", exc)

    # 3. 异步运行 RAG 评估，不阻断主流程
    rag_evaluation: dict = {}
    try:
        from rag.evaluator import run_turn_evaluation
        from db.queries import save_rag_evaluation

        # 收集本轮的检索上下文
        tool_calls_log = state.get("tool_calls_log", [])        # 从 state 里取工具调用日志
        # 本轮生成和判断时实际用到的简历/JD 检索结果摘要。
        retrieved_chunks = [
            tc["result_preview"]
            for tc in tool_calls_log
            if tc.get("tool") in ("search_resume", "search_jd") and tc.get("success")
        ]
        # 基于问题、回答、检索上下文、RAG 命中结果和真实分数，对当前轮进行一次 RAG 质量评估
        rag_evaluation = await run_turn_evaluation(
            question=state["current_question"],
            answer=state["current_answer"],
            generated_next_question="",  # 下一个问题还没生成，此处留空
            retrieved_chunks=retrieved_chunks,
            rag_matches=state.get("current_rag_matches", []),
            actual_score=grading.get("score", 3),
        )
        # 保存 RAG 评估结果到数据库
        save_rag_evaluation(
            session_id=state["session_id"],
            turn_number=state.get("turn_count", 0),
            metrics=rag_evaluation,
            tool_calls=tool_calls_log,
            message_id=message_id,
        )
    except Exception as exc:
        logger.warning("RAG evaluation failed: %s", exc)
    # LangGraph 会把这个返回值合并进当前 state。
    # 执行完这个节点后，state 里会新增或更新：state["rag_evaluation"]
    return {"rag_evaluation": rag_evaluation}


# ── Routing functions ──────────────────────────────────────────────────────────

def _should_continue_or_replan(state: InterviewState) -> str:
    """index_answer 完成后的分流决策：结束 / 重新规划 / 继续下一题。"""
    if state.get("session_complete"):
        return END
    if _should_replan(state):
        return "planner"
    return "interviewer"


# ── Graph builder ──────────────────────────────────────────────────────────────

# 全局 MemorySaver 检查点
# 当前所有 session 的 graph 状态，都会保存在这个内存 checkpointer 里
# 同一个进程里多个 session 可以共享它
_checkpointer = MemorySaver()


def build_unified_graph() -> StateGraph:
    """
        构建统一面试 Graph。
        使用 interrupt_before=["grader"] 使图在 grader 节点前暂停，
        等待外部（API 层）更新用户回答后再继续执行。
    """
    # 创建图对象，指定 state 类型为 InterviewState
    graph = StateGraph(InterviewState)

    # 注册所有节点
    graph.add_node("planner", planner_node)
    graph.add_node("interviewer", interviewer_node)
    graph.add_node("grader", grader_node)
    graph.add_node("critic", critic_node)
    graph.add_node("followup", followup_node)
    graph.add_node("coach", coach_node)
    graph.add_node("index_answer", index_answer_node)

    # ── 入口点：planner 
    graph.set_entry_point("planner")
    # planner -> interviewer
    graph.add_edge("planner", "interviewer")

    # ── interviewer 提问后等待回答（interrupt 在 grader 前）
    # 图结构上，下一步确实是 grader，但由于设置了 interrupt_before=["grader"]，执行到这里会暂停，等 API 层把用户回答写入 state 后再继续。
    graph.add_edge("interviewer", "grader")

    # ── 回答后的完整评估管道
    graph.add_edge("grader", "critic")
    graph.add_edge("critic", "followup")
    graph.add_edge("followup", "coach")
    graph.add_edge("coach", "index_answer")

    # ── 评估完成后路由：结束 / 重新规划 / 下一题
    graph.add_conditional_edges(
        "index_answer",
        _should_continue_or_replan,
        {
            "planner": "planner",
            "interviewer": "interviewer",
            END: END,
        },
    )

    return graph


# 编译为可执行图，加载 MemorySaver 检查点，并在 grader 前设置中断点
compiled_graph = build_unified_graph().compile(
    checkpointer=_checkpointer,     #这张可执行图的状态检查点存储，用的就是前面那个人工创建的 MemorySaver
    interrupt_before=["grader"],    #当图执行到“下一步即将进入 grader”时，先中断
)

# ── API 层辅助函数 ──────────────────────────────────────────────────────

def get_thread_config(session_id: str) -> dict:
    """生成 LangGraph thread 配置，用于所有 graph 操作。"""
    return {"configurable": {"thread_id": session_id}}

def get_current_state(session_id: str) -> dict:
    """给 API 层一个简单入口，按 session_id 取当前 graph state"""
    config = get_thread_config(session_id)
    snapshot = compiled_graph.get_state(config)
    if snapshot is None:
        return {}
    return snapshot.values or {}

def restore_state_to_checkpointer(session_id: str, state: dict) -> None:
    """
        将外部 state（如 DB 快照）注入 checkpointer，用于服务重启后恢复。
        as_node="interviewer" 告知 LangGraph：状态是面试官刚提完问，
        下次 ainvoke 将从 grader 开始（即等待用户回答后继续）。
    """
    config = get_thread_config(session_id)
    compiled_graph.update_state(config, state, as_node="interviewer")
