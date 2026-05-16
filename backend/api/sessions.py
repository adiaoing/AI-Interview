"""
    面试会话 API — 适配统一 Graph + MemorySaver Checkpointer。
"""
from __future__ import annotations
import json
import os

from fastapi import APIRouter, File, HTTPException, Header, UploadFile
from pydantic import BaseModel #数据校验和解析
from agents.state import InterviewState
from agents.graph import (
    compiled_graph,  #核心执行 graph 对象
    get_thread_config, #根据 session_id 拿到 session 对应的 graph 配置
    get_current_state,  #从 checkpointer 拿到当前 graph 状态
    restore_state_to_checkpointer,  #把状态恢复到 checkpointer（服务重启后从 DB 快照恢复时用)
)
from db.queries import (
    create_session, 
    get_session,    
    complete_session,                       # 标记完成
    save_message,
    get_messages,
    get_competency_scores,                  # 查能力评分
    save_session_state_snapshot,            # 存状态快照
    get_latest_session_state_snapshot,      # 查最新快照
    get_rag_evaluations,                    # 查 RAG 评估结果
)

from rag.documents import extract_uploaded_document_text, index_session_job_description, index_session_resume
'''
    extract_uploaded_document_text ：从文件字节里抽文本
    index_session_job_description ：把岗位描述做索引
    index_session_resume ：把简历内容做索引
'''

# @router.post、@router.get，都挂在这个 router 上
router = APIRouter()

# 从环境变量里读取配置
MAX_TURNS = int(os.getenv("MAX_TURNS", "8"))                                        # 一场面试最多几轮
MAX_DOCUMENT_CHARS = int(os.getenv("MAX_DOCUMENT_CHARS", "30000"))                  # 上传的简历最大字符数
MAX_DOCUMENT_BYTES = int(os.getenv("MAX_DOCUMENT_BYTES", str(5 * 1024 * 1024)))     # 上传文件最大字节数默认 5MB

'''
    “创建 session”接口接收的 body 结构
    前端发：
        {
            "interview_type": "behavioral",
            "role": "Backend Engineer",
            "difficulty": 4
        }
'''
class CreateSessionRequest(BaseModel):

    interview_type: str  # behavioral | technical | general
    role: str | None = None
    difficulty: int = 3

class TurnRequest(BaseModel):
    # 提交一轮回答时，前端 body 里只传：answer
    answer: str

class DocumentTextRequest(BaseModel):
    # 上传简历文本或 JD 文本时，前端 body 里传：content 和 filename（可选）
    content: str
    filename: str | None = None

# 把上传文件变成 (文件名, 文件字节) 返回，并校验大小限制
async def _read_document_upload(file: UploadFile) -> tuple[str, bytes]:
    filename = file.filename or "uploaded-document"
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file cannot be empty")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=400, detail=f"Uploaded file exceeds {MAX_DOCUMENT_BYTES} bytes")
    return filename, data

# 新创建一份全新的初始 state 字典
def _build_default_state(
    session_id: str,
    user_id: str,
    interview_type: str,
    role: str | None,
    difficulty: int,
) -> InterviewState:
    return {
        "session_id": session_id,                       # 面试会话 ID
        "user_id": user_id,                             # 用户 ID
        "interview_type": interview_type,               # 面试类型：behavioral | technical | general
        "role": role or "Software Engineer",            # 面试岗位
        "difficulty": difficulty,                       # 面试难度等级，1-5
        "turn_count": 0,                                # 当前轮数
        "max_turns": MAX_TURNS,                         # 最大轮数
        "messages": [],                                 # 整场对话历史
        "competency_scores": {},                        # 整体能力维度分数
        "current_question": "",                         # 当前题目
        "current_question_is_followup": False,          # 当前题是不是追问
        "current_answer": "",                           # 当前回答
        "current_message_id": None,                     # 当前消息在数据库里的 id
        "grading": {},                                  # 当前回答的评分结果
        "current_rag_matches": [],                      # 当前轮次命中的相似历史片段
        "current_user_memory_matches": [],              # 当前轮次命中的用户历史记忆片段
        "recurring_weakness_detected": False,           # 是否检测到重复弱点
        "rag_insights": [],                             # RAG 相关的洞察（如用户回答缺哪些关键信息）    
        "follow_up_needed": False,                      # 是否需要追问
        "follow_up_question": "",                       # 追问内容
        "session_complete": False,                      # 会话是否完成
        "coaching_notes": [],                           # 教练建议
        "tts_audio": None,                              # TTS 音频数据
    #------------- new add ---------------
        "interview_plan": {},
        "plan_updated_at": 0,
        "tool_calls_log": [],
        "rag_evaluation": {},
    }

# 把 tts_audio 置空，避免状态太大,将当前运行态 state 转成适合保存到数据库的精简版 snapshot
def _serialize_state_for_snapshot(state: dict) -> dict:
    """去掉大体积 TTS 音频后序列化 state。"""
    snapshot = json.loads(json.dumps(state))    # 把 state 先转成 JSON 再转回来，得到一个新的、纯净的、可序列化的字典副本
    snapshot["tts_audio"] = None                # tts_audio 置空
    return snapshot

# 把当前 state 序列化后存到 DB
def _save_state_snapshot(state: dict, snapshot_stage: str) -> None:
    save_session_state_snapshot(
        session_id=state["session_id"],
        user_id=state["user_id"],
        turn_number=state.get("turn_count", 0),
        state=_serialize_state_for_snapshot(state),
        snapshot_stage=snapshot_stage,
    )


def _ensure_checkpointer_state(session: dict, user_id: str) -> bool:
    """
        graph 运行态如果还在，就直接用，如果不在，就从数据库快照恢复
    """
    #--------- 如果存在 ----------- 
    session_id = session["id"]
    config = get_thread_config(session_id)
    snapshot = compiled_graph.get_state(config)     # graph 的 checkpointer
    if snapshot and snapshot.values:
        return True  # checkpointer 中已有状态

    #--------- 如果不在，尝试从 DB 快照恢复 ----------- 
    db_snapshot = get_latest_session_state_snapshot(session_id)
    if not db_snapshot:
        return False
    #先造一份完整默认 state（快照里有可能缺一些字段，先造一份完整的更稳）
    restored = _build_default_state(
        session_id=session_id,
        user_id=user_id,
        interview_type=session["interview_type"],
        role=session.get("role"),
        difficulty=session.get("difficulty") or 3,
    )
    # 把数据库里存的 state 内容覆盖到默认 state 上
    restored.update(db_snapshot.get("state") or {})
    # 再次强制写回，避免快照里这两个字段有问题（以防万一）
    restored["session_id"] = session_id
    restored["user_id"] = user_id
    # 把恢复好的 state 写回 graph 的 checkpointer
    restore_state_to_checkpointer(session_id, restored)
    return True


# ── 第一个接口：创建会话 拿到 session_id ───────────────────────────────────────────────────────────
@router.post("")

async def create_interview_session(
    body: CreateSessionRequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
):
    '''
        body : 请求体会被解析成 CreateSessionRequest 对象
        x_user_id : 从请求头里拿到用户 ID
    '''
    if body.interview_type not in ("behavioral", "technical", "general"):
        raise HTTPException(status_code=400, detail="Invalid interview_type")
    if not (1 <= body.difficulty <= 5):
        raise HTTPException(status_code=400, detail="Difficulty must be 1-5")
    # 把当前用户、面试类型、岗位，交给 db.queries.create_session(...) 去数据库里创建一条新记录
    session = create_session(
        user_id=x_user_id,
        interview_type=body.interview_type,
        role=body.role,
    )
    # create_session(...) 返回的是一个字典，取 id 字段，后面所有 state、snapshot 都用这个 session_id
    session_id = session["id"]

    # 构造初始 state ，把刚才请求里的 5 个核心信息存入 state
    initial_state = _build_default_state(
        session_id=session_id,
        user_id=x_user_id,
        interview_type=body.interview_type,
        role=body.role,
        difficulty=body.difficulty,
    )
    # 一创建 session，就立刻把初始 state 作为 "created" 阶段的快照存入数据库
    _save_state_snapshot(initial_state, snapshot_stage="created")

    return {"session_id": session_id}

# POST 接口 ： 上传简历文本，{session_id} 是路径参数，表示这份简历文本上传到哪一场面试 session 里
@router.post("/{session_id}/resume")
async def upload_resume_text(
    session_id: str,
    body: DocumentTextRequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
):
    '''
    body : DocumentTextRequest
        {
            "content": "这是简历正文内容",
            "filename": "resume.txt"
        }

    返回一个 result 字典给前端,示例：
        {
            "document_id": "doc_001",               建了一条文档记录
            "chunk_count": 12,                      被切成了多少块
            "status": "completed"                   当前处理状态是什么
        }

    '''
    # 去数据库查这场 session 是否存在
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    # session 存在且属于当前用户，允许往里面上传简历
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Resume content cannot be empty")
    if len(content) > MAX_DOCUMENT_CHARS:
        raise HTTPException(status_code=400, detail=f"Resume content exceeds {MAX_DOCUMENT_CHARS} characters")
    # 简历文本非空且长度不超过限制，开始索引简历
    try:
        result = await index_session_resume(
            session_id=session_id,
            user_id=x_user_id,
            content=content,
            source_type="text",
            filename=body.filename,
            role=session.get("role"),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to index resume: {exc}") from exc
    
    return {
        "document_id": result["document"]["id"],
        "chunk_count": result["chunk_count"],
        "status": result["document"]["status"],
    }

# POST 接口 ： 上传简历文件
@router.post("/{session_id}/resume/file")
async def upload_resume_file(
    session_id: str,
    file: UploadFile = File(...),           # 前端要用 multipart/form-data 方式传文件 
    x_user_id: str = Header(..., alias="X-User-Id"),
):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    filename, data = await _read_document_upload(file)
    try:
        content = extract_uploaded_document_text(filename, data)
        result = await index_session_resume(
            session_id=session_id,
            user_id=x_user_id,
            content=content,
            source_type="upload",
            filename=filename,
            role=session.get("role"),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to index resume file: {exc}") from exc

    return {
        "document_id": result["document"]["id"],
        "chunk_count": result["chunk_count"],
        "status": result["document"]["status"],
    }

# 上传岗位描述文本
@router.post("/{session_id}/job-description")
async def upload_job_description_text(
    session_id: str,
    body: DocumentTextRequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Job description content cannot be empty")
    if len(content) > MAX_DOCUMENT_CHARS:
        raise HTTPException(status_code=400, detail=f"Job description content exceeds {MAX_DOCUMENT_CHARS} characters")
    # 调用岗位描述索引函数
    try:
        result = await index_session_job_description(
            session_id=session_id,
            user_id=x_user_id,
            content=content,
            source_type="text",
            filename=body.filename,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to index job description: {exc}") from exc

    return {
        "document_id": result["document"]["id"],
        "chunk_count": result["chunk_count"],
        "status": result["document"]["status"],
    }

# 上传岗位描述文件
@router.post("/{session_id}/job-description/file")
async def upload_job_description_file(
    session_id: str,
    file: UploadFile = File(...),
    x_user_id: str = Header(..., alias="X-User-Id"),
):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    filename, data = await _read_document_upload(file)
    try:
        content = extract_uploaded_document_text(filename, data)
        result = await index_session_job_description(
            session_id=session_id,
            user_id=x_user_id,
            content=content,
            source_type="upload",
            filename=filename,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to index job description file: {exc}") from exc

    return {
        "document_id": result["document"]["id"],
        "chunk_count": result["chunk_count"],
        "status": result["document"]["status"],
    }

# ── 真正开始一场面试，跑 graph，拿到第一题 ───────────────────────────────────────────────────
@router.post("/{session_id}/start")
async def start_session(session_id: str, x_user_id: str = Header(..., alias="X-User-Id")):
    # 先查 session
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    # 拿 graph 的配置 （告诉 graph：现在操作的是哪一个 session 对应的线程/状态）
    config = get_thread_config(session_id)

    # 处理“重复调用 /start” 的情况：如果 checkpointer 里已经有状态了，就直接返回当前题（可能是第一题，也可能是之前的题），不重新跑图了
    current = get_current_state(session_id)   # 从 checkpointer 拿当前状态
    if current.get("current_question") and current.get("messages"):
        return {
            "question": current["current_question"],
            "tts_audio": current.get("tts_audio"),
            "turn": 1,
            "difficulty": current["difficulty"],
            "session_complete": False,
            "interview_plan": current.get("interview_plan", {}),
        }

    # 构造初始状态，从 DB 快照读取配置（difficulty 等可能在 create 时设置）
    db_snapshot = get_latest_session_state_snapshot(session_id)
    # 构造一份新的默认 state
    initial_state = _build_default_state(
        session_id=session_id,
        user_id=x_user_id,
        interview_type=session["interview_type"],
        role=session.get("role"),
        difficulty=session.get("difficulty") or 3,
    )
    if db_snapshot and db_snapshot.get("state"):
        # 如果数据库里确实查到了快照，而且快照里有 state 字段，就把快照里的 state 内容覆盖到默认 state 上（以防万一，先造一份完整的默认 state，再覆盖，这样即使快照里缺字段也不怕）
        saved = db_snapshot["state"]
        initial_state["difficulty"] = saved.get("difficulty", initial_state["difficulty"])
        initial_state["max_turns"] = saved.get("max_turns", MAX_TURNS)

    # 首次运行图：planner → interviewer → 在 grader 前中断
    try:
        await compiled_graph.ainvoke(initial_state, config=config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {exc}") from exc
    # 从当前 state 中拿首题
    state = get_current_state(session_id)
    question = state.get("current_question", "")
    if not question:
        raise HTTPException(status_code=500, detail="Interviewer failed to generate question")

    # 这是 /start，那现在生成的是第一题，所以 turn 固定为 1
    turn = 1
    # 把首题保存到数据库
    msg = save_message(
        session_id=session_id,
        role="interviewer",
        content=question,
        turn_number=turn,
    )
    # 更新 checkpointer 中的消息列表（让 graph 的运行态 messages 和数据库里的 message 记录对齐）
    compiled_graph.update_state(config, {
        "messages": [{
            "role": "interviewer",
            "content": question,
            "turn_number": turn,
            "id": msg["id"],
        }],
    })
    # 保存 “started” 阶段的 snapshot
    _save_state_snapshot(get_current_state(session_id), snapshot_stage="started")
    # start 阶段最后返回（第一题文本、TTS 音频、turn固定是 1，难度等级、面试计划等）给前端
    return {
        "question": question,
        "tts_audio": state.get("tts_audio"),
        "turn": turn,
        "difficulty": state["difficulty"],
        "session_complete": False,          #开始阶段当然还没结束，所以是 False
        "interview_plan": state.get("interview_plan", {}),  #如果 planner 节点写了面试计划，这里也一起返回给前端
    }

# 用户回答一题之后的核心处理流程
@router.post("/{session_id}/turn")
async def submit_turn(
    session_id: str,
    body: TurnRequest,  #"answer": "回答内容"
    x_user_id: str = Header(..., alias="X-User-Id"),
):
    """
        1. 收到用户答案
        2. 写入数据库
        3. 写入 graph state
        4. 恢复图执行
        5. 让后面的 grader / followup / coach 去处理
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # 先确保 graph 运行态是可用的
    if not _ensure_checkpointer_state(session, x_user_id):
        raise HTTPException(
            status_code=400,
            detail="Session state not found. Please call /start first.",
        )
    # 先拿当前 session 对应的 graph 配置
    config = get_thread_config(session_id)
    # 读取这场 session 当前的 graph state
    current = get_current_state(session_id)
    if current.get("session_complete"):
        raise HTTPException(status_code=400, detail="Session already completed")

    # 把用户回答先保存到数据库
    current_turn = current.get("turn_count", 0) + 1
    user_msg = save_message(
        session_id=session_id,
        role="user",
        content=body.answer,
        turn_number=current_turn,
    )

    # 把用户回答写进 graph state
    messages = list(current.get("messages", []))    #先把当前 messages 拿出来
    messages.append({
        "role": "user",
        "content": body.answer,
        "turn_number": current_turn,
        "id": user_msg["id"],
    })
    # 把多个字段一起写回 graph
    compiled_graph.update_state(config, {
        "current_answer": body.answer,
        "turn_count": current_turn,
        "current_message_id": user_msg["id"],
        "messages": messages,
    })

    # 恢复 Graph 执行：grader → critic → followup → coach → index_answer → ...
    try:
        #基于 update_state 更新后的现有 state，继续往下执行
        await compiled_graph.ainvoke(None, config=config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {exc}") from exc

    # ----graph 跑完了，现在回头去 state 里拿它产出的结果------
    state = get_current_state(session_id)
    grading = state.get("grading", {})
    competency = grading.get("competency", "general")
    score = grading.get("score", 3)

    # 把评分结果回填到数据库里的那条用户消息
    from db.client import get_client
    get_client().table("messages").update({
        "competency": competency,
        "score": score,
    }).eq("id", user_msg["id"]).execute()

    if state.get("session_complete"):
        complete_session(session_id, state["difficulty"])
        _build_final_report(state, session_id)
        _save_state_snapshot(state, snapshot_stage="completed")
        return {
            "session_complete": True,
            "grading": grading,
            "coaching_note": state["coaching_notes"][-1] if state.get("coaching_notes") else "",
            "current_rag_matches": state.get("current_rag_matches", []),
            "recurring_weakness_detected": state.get("recurring_weakness_detected", False),
            "rag_evaluation": state.get("rag_evaluation", {}),
            "tool_calls_log": state.get("tool_calls_log", []),
            "question": None,
            "tts_audio": None,
            "turn": current_turn,
            "difficulty": state["difficulty"],
        }

    # 保存下一个面试官问题到 DB
    next_turn = current_turn + 1
    next_question = state.get("current_question", "")
    next_msg = save_message(
        session_id=session_id,
        role="interviewer",
        content=next_question,
        turn_number=next_turn,
        is_followup=bool(state.get("current_question_is_followup")),
    )
    # 同步消息列表到 checkpointer
    messages = list(state.get("messages", []))
    messages.append({
        "role": "interviewer",
        "content": next_question,
        "turn_number": next_turn,
        "is_followup": bool(state.get("current_question_is_followup")),
        "id": next_msg["id"],
    })
    compiled_graph.update_state(config, {"messages": messages})

    _save_state_snapshot(get_current_state(session_id), snapshot_stage="turn")

    return {
        "session_complete": False,
        "grading": grading,
        "coaching_note": state["coaching_notes"][-1] if state.get("coaching_notes") else "",
        "current_rag_matches": state.get("current_rag_matches", []),
        "recurring_weakness_detected": state.get("recurring_weakness_detected", False),
        "rag_evaluation": state.get("rag_evaluation", {}),
        "tool_calls_log": state.get("tool_calls_log", []),
        "question": next_question,
        "tts_audio": state.get("tts_audio"),
        "turn": next_turn,
        "difficulty": state["difficulty"],
        "is_followup": bool(state.get("current_question_is_followup")),
        "interview_plan": state.get("interview_plan", {}),
    }


# ── 获取整场面试报告 ───────────────────────────────────────────────────────────

@router.get("/{session_id}/report")
async def get_report(session_id: str, x_user_id: str = Header(..., alias="X-User-Id")):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    # 读取数据库里的 messages ，去数据库取这场 session 的全部消息
    messages = get_messages(session_id)
    competency_scores = get_competency_scores(session_id)
    # 读取当前 graph state
    state = get_current_state(session_id) or {}
    coaching_notes = state.get("coaching_notes", [])
    # 从 messages 里筛出有分数的消息
    scored_messages = [m for m in messages if m.get("score") is not None]
    # 计算所有已评分消息的平均分
    overall_score = (
        sum(m["score"] for m in scored_messages) / len(scored_messages)
        if scored_messages else 0
    )
    # 返回报告内容
    return {
        "session": session,
        "overall_score": round(overall_score, 2),
        "competency_scores": competency_scores,
        "coaching_notes": coaching_notes,
        "rag_insights": state.get("rag_insights", []),      # 从当前 graph state 里取 RAG 洞察
        "interview_plan": state.get("interview_plan", {}),  # 从当前 graph state 里取面试计划
        "messages": messages,
        "total_turns": len([m for m in messages if m["role"] == "user"]),
    }


@router.get("/{session_id}/rag-metrics")
async def get_rag_metrics(session_id: str, x_user_id: str = Header(..., alias="X-User-Id")):
    """返回本 session 的 RAG 评估指标汇总。"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    # 获取这场 session 的 RAG 评估记录
    evaluations = get_rag_evaluations(session_id)
    if not evaluations:
        return {"session_id": session_id, "turns_evaluated": 0, "summary": {}, "per_turn": []}

    # 把原列表里不是 None 的值挑出来，安全计算平均值
    def safe_avg(values: list) -> float | None:
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None
    # 把每种分数先抽成列表
    cp_scores = [e.get("context_precision") for e in evaluations]       # 上下文精度
    faith_scores = [e.get("faithfulness") for e in evaluations]         # 忠实度
    ar_scores = [e.get("answer_relevancy") for e in evaluations]        # 回答相关性
    agg_scores = [e.get("aggregate_score") for e in evaluations]        # 综合分
    # 取弱点检测结果并统计 TP/FP/FN/TN
    wd_results = [e.get("weakness_detection_outcome") for e in evaluations if e.get("weakness_detection_outcome")]
    tp = wd_results.count("TP")
    fp = wd_results.count("FP")
    fn = wd_results.count("FN")
    tn = wd_results.count("TN")
    # 算 precision / recall
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None

    # 工具调用统计
    all_tool_calls = []
    for e in evaluations:
        calls = e.get("tool_calls") or []
        all_tool_calls.extend(calls)
    tool_usage: dict[str, int] = {}
    for tc in all_tool_calls:
        name = tc.get("tool", "unknown")
        tool_usage[name] = tool_usage.get(name, 0) + 1

    return {
        "session_id": session_id,
        "turns_evaluated": len(evaluations),
        "summary": {
            "avg_context_precision": safe_avg(cp_scores),
            "avg_faithfulness": safe_avg(faith_scores),
            "avg_answer_relevancy": safe_avg(ar_scores),
            "avg_aggregate_score": safe_avg(agg_scores),
            "weakness_detection": {
                "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                "precision": round(precision, 3) if precision is not None else None,
                "recall": round(recall, 3) if recall is not None else None,
            },
            "tool_usage": tool_usage,
        },
        "per_turn": [
            {
                "turn_number": e["turn_number"],
                "context_precision": e.get("context_precision"),
                "faithfulness": e.get("faithfulness"),
                "answer_relevancy": e.get("answer_relevancy"),
                "aggregate_score": e.get("aggregate_score"),
                "weakness_detection_outcome": e.get("weakness_detection_outcome"),
                "retrieved_chunks_count": e.get("retrieved_chunks_count", 0),
                "rag_matches_count": e.get("rag_matches_count", 0),
            }
            for e in evaluations
        ],
    }

# 获取历史记录，给前端一个简单的聊天历史读取口
@router.get("/{session_id}/history")
async def get_history(session_id: str, x_user_id: str = Header(..., alias="X-User-Id")):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"messages": get_messages(session_id)}


def _build_final_report(state: dict, session_id: str) -> None:
    if not state.get("coaching_notes"):
        return
    summary = "\n".join(f"• {note}" for note in state["coaching_notes"])
    save_message(
        session_id=session_id,
        role="coach",
        content=summary,
        turn_number=state.get("turn_count", 0) + 1,
    )
