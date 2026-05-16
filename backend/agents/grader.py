from __future__ import annotations
import json
from agents.state import InterviewState
from agents.llm import generate_text
'''
    competency : 当前这条回答主要体现的能力项名称
    feedback : 2~3 句建设性反馈
    strengths : 2~3 点具体优点，必须引用候选人回答中的内容
    gaps : 2~3 点具体不足，必须指出缺少的具体信息
    follow_up_suggestion : 如果需要追问，给一个追问建议；如果不需要追问，这里填 null
'''
GRADER_SYSTEM = """你是一名中文技术面试评估官。请评估候选人的回答，并返回 JSON object。

Return ONLY valid JSON with this exact structure:
{
  "score": <integer 1-5>,
  "competency": "<primary competency demonstrated>",
  "feedback": "<2-3 sentence constructive feedback>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "gaps": ["<gap 1>", "<gap 2>"],
  "follow_up_suggestion": "<optional: suggested follow-up question if answer was weak or incomplete, else null>"
}

Scoring rubric:
1 = No meaningful answer or completely off-topic
2 = Partial answer, missing key elements
3 = Adequate answer, covers basics
4 = Strong answer, well-structured, specific examples
5 = Exceptional answer, demonstrates mastery

反馈要求：
- feedback、strengths、gaps 必须使用中文。
- feedback 不要写空泛评价，比如“工程落地意识强”“体现扎实习惯”。
- strengths 必须引用候选人回答中的具体内容。
- gaps 必须指出缺少的具体信息，例如项目背景、本人职责、关键指标、异常链路、技术取舍或最终结果。
- follow_up_suggestion 如果需要追问，也必须是一个具体中文问题。
"""

# 主函数
async def grader_node(state: InterviewState) -> dict:
    prompt = (
        f"Question: {state['current_question']}\n\n"
        f"Candidate's answer: {state['current_answer']}\n\n"
        f"Interview type: {state['interview_type']}\n"
        f"Role: {state.get('role', 'Software Engineer')}\n"
        f"Difficulty level: {state['difficulty']}/5"
    )
    # 调用 LLM 生成评分 JSON
    raw = await generate_text(system=GRADER_SYSTEM, prompt=prompt, max_tokens=1024)
    # 处理模型有时会返回这种形式
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    grading = json.loads(raw.strip())

    # 更新 competency_scores
    competency = grading.get("competency", "general")
    score = grading.get("score", 3)
    # 复制当前已有的 competency_scores
    updated_scores = dict(state.get("competency_scores", {}))
    if competency in updated_scores:
        prev = updated_scores[competency]
        updated_scores[competency] = (prev + score) / 2
    else:
        updated_scores[competency] = float(score)

    return {
        "grading": grading,
        "competency_scores": updated_scores,
    }
