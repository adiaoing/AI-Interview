from __future__ import annotations

import json
import logging
import os
from typing import Callable, Awaitable

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None

# 返回一个可复用的 AsyncOpenAI 客户端
def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.environ["DASHSCOPE_API_KEY"],
            base_url=os.getenv(
                "DASHSCOPE_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        )
    return _client

# 普通文本生成
async def generate_text(system: str, prompt: str, max_tokens: int = 512) -> str:
    client = _get_client()
    response = await client.chat.completions.create(
        model=os.getenv("DASHSCOPE_CHAT_MODEL", "qwen-plus"),
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


async def generate_with_tools(
    system: str,
    prompt: str,
    tools: list[dict],
    tool_executor: Callable[[str, dict], Awaitable[str]],
    max_rounds: int = 5,
    max_tokens: int = 1024,
) -> tuple[str, list[dict]]:
    """
    ReAct 循环：
        LLM 可以自己决定：
            要不要调工具
            调哪个工具
            拿到工具结果后再继续思考
            最后生成最终答案。
    Returns:
        (final_answer, tool_calls_log)
    """
    client = _get_client()
    model = os.getenv("DASHSCOPE_CHAT_MODEL", "qwen-plus")
    # 初始化 messages
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    tool_calls_log: list[dict] = []
    # ReAct 主循环
    for round_idx in range(max_rounds):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",     # 让模型自己决定要不要调工具、调哪个工具
                max_tokens=max_tokens,
            )
        except Exception as exc:
            logger.warning("LLM call failed in round %d: %s", round_idx, exc)
            break

        choice = response.choices[0]
        message = choice.message

        # 没有工具调用 → 直接返回最终答案
        if not message.tool_calls:
            return (message.content or "").strip(), tool_calls_log

        # 将 assistant 消息（含 tool_calls）加入历史
        assistant_msg: dict = {"role": "assistant", "content": message.content or ""}
        assistant_msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in message.tool_calls
        ]
        messages.append(assistant_msg)

        # 执行每个工具调用
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            try:
                tool_args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                tool_args = {}

            try:
                tool_result = await tool_executor(tool_name, tool_args)
                tool_calls_log.append({
                    "round": round_idx,
                    "tool": tool_name,
                    "args": tool_args,
                    "result_preview": str(tool_result)[:300],
                    "success": True,
                })
            except Exception as exc:
                tool_result = f"工具执行失败：{exc}"
                tool_calls_log.append({
                    "round": round_idx,
                    "tool": tool_name,
                    "args": tool_args,
                    "error": str(exc),
                    "success": False,
                })
                logger.warning("Tool %s failed: %s", tool_name, exc)

            # 把工具结果追加到消息历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_result),
            })

    # 超出最大轮次后，强制生成最终答案（不带工具）
    logger.warning("ReAct max_rounds (%d) reached, forcing final answer", max_rounds)
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip(), tool_calls_log
    except Exception as exc:
        logger.error("Final answer generation failed: %s", exc)
        return "", tool_calls_log
