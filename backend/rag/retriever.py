

from __future__ import annotations
from rag.embeddings import embed_text
from db.queries import find_similar_embeddings, save_embedding


async def index_answer(
    session_id: str,
    message_id: str,
    question: str,
    answer: str,
    competency: str | None,
    score: int | None,
) -> None:
    """
        将本轮回答写入历史 RAG。
        注意：展示内容仍保留“问题 + 回答”，但用于相似度检索的 embedding
        以回答文本为主，避免题目文本过度主导“历史弱点”匹配结果。
    """
    combined = f"Question: {question}\nAnswer: {answer}"
    embedding_text = _build_gap_embedding_text(question=question, answer=answer)
    embedding = await embed_text(embedding_text)
    save_embedding(
        session_id=session_id,
        message_id=message_id,
        embedding=embedding,
        content=combined,
        metadata={
            "competency": competency,
            "score": score,
            "question": question,
            "answer": answer,
            "embedding_mode": "answer_first",
        },
    )


async def find_gaps(
    session_id: str,
    current_question: str,
    current_answer: str,
    threshold: float = 0.75,
    limit: int = 4,
) -> list[dict]:
    """
        查找语义上相似的历史回答，用来判断候选人是否反复暴露同类弱点。
        这里的 query embedding 以当前回答为主，而不是完整题面。
    """
    query = _build_gap_embedding_text(question=current_question, answer=current_answer)
    embedding = await embed_text(query)
    return find_similar_embeddings(
        session_id=session_id,
        query_embedding=embedding,
        threshold=threshold,
        limit=limit,
    )


def _build_gap_embedding_text(question: str, answer: str) -> str:
    """
        构造用于历史弱点检索的 embedding 文本。
            默认用“回答为主、问题为辅”的策略：
            - 主要比较候选人的回答方式、缺失信息和表达深度
            - 只把问题作为轻量上下文，避免相似题面把相似度抬得过高
    """
    normalized_answer = (answer or "").strip()
    normalized_question = (question or "").strip()

    if normalized_answer and normalized_question:
        return (
            f"Candidate answer: {normalized_answer}\n"
            f"Interview context: {normalized_question}"
        )
    if normalized_answer:
        return f"Candidate answer: {normalized_answer}"
    return f"Interview context: {normalized_question}"
