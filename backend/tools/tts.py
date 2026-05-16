from __future__ import annotations
import asyncio
import base64
import os
import httpx

# In-memory interrupt flags per session
_interrupt_flags: dict[str, bool] = {}


def set_interrupt(session_id: str) -> None:
    _interrupt_flags[session_id] = True


def clear_interrupt(session_id: str) -> None:
    _interrupt_flags[session_id] = False


def is_interrupted(session_id: str) -> bool:
    return _interrupt_flags.get(session_id, False)


async def generate_tts(text: str, session_id: str) -> str | None:
    """
    Generate TTS audio using ElevenLabs.
    Returns base64-encoded MP3 audio, or None on failure / interrupt.
    Falls back gracefully so callers always get text even without audio.
    """
    clear_interrupt(session_id)
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        return None

    voice_id = "EXAVITQu4vr4xnSDxMaL"  # Rachel — clear, professional
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                return None

            if is_interrupted(session_id):
                return None

            audio_bytes = response.content
            return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception:
        return None


# Anthropic tool schema definition (swappable when Anthropic ships TTS)
TTS_TOOL_SCHEMA = {
    "name": "generate_speech",
    "description": (
        "Convert text to spoken audio. Use this to vocalize the current interview question. "
        "Returns base64-encoded MP3 audio. If synthesis fails, the question text is used as fallback."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to synthesize into speech.",
            },
            "session_id": {
                "type": "string",
                "description": "Session ID for interrupt tracking.",
            },
        },
        "required": ["text", "session_id"],
    },
}
