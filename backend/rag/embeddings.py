from __future__ import annotations
import os
from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None


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


async def embed_text(text: str) -> list[float]:
    """Embed text using DashScope's OpenAI-compatible embedding API."""
    client = _get_client()
    response = await client.embeddings.create(
        model=os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4"),
        input=text,
        dimensions=int(os.getenv("DASHSCOPE_EMBEDDING_DIMENSIONS", "1536")),
    )
    return response.data[0].embedding
