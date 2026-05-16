from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tools.tts import generate_tts, set_interrupt

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    session_id: str


class InterruptRequest(BaseModel):
    session_id: str


@router.post("")
async def synthesize(body: TTSRequest):
    """Generate TTS audio for arbitrary text. Returns base64 MP3 or null."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    audio = await generate_tts(body.text, body.session_id)
    return {"audio": audio, "text": body.text}


@router.post("/interrupt")
async def interrupt(body: InterruptRequest):
    """Signal TTS interrupt for a session (stops current synthesis)."""
    set_interrupt(body.session_id)
    return {"interrupted": True, "session_id": body.session_id}
