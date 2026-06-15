import base64
import uuid
from fastapi import APIRouter, UploadFile, File, Form, Depends
from core.auth import get_current_user
from services.stt_service import transcribe_bytes
from services.tts_service import synthesize_to_bytes
from agents.graph import run_agent
from db.mongo import get_collection
from db.models import MessageInDB

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/upload")
async def voice_upload(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    mode: str = Form("ai_speaks"),
    user=Depends(get_current_user),
):
    audio_bytes = await audio.read()
    fmt = audio.filename.rsplit(".", 1)[-1] if "." in audio.filename else "webm"

    stt = await transcribe_bytes(audio_bytes, fmt)
    scammer_text = stt.get("text", "")

    col_msg = get_collection("messages")
    history_docs = await col_msg.find(
        {"session_id": session_id},
        {"_id": 0, "sender": 1, "content": 1},
        sort=[("timestamp", -1)],
        limit=6,
    ).to_list(6)
    history = [{"speaker": d["sender"], "text": d["content"]} for d in reversed(history_docs)]

    result = await run_agent(
        scammer_text=scammer_text,
        history=history,
        mode="ai_takeover" if mode == "ai_speaks" else "ai_coached",
    )
    reply = result.get("ai_response") or result.get("coaching_text", "")

    audio_b64 = ""
    if mode == "ai_speaks" and reply:
        tts_bytes = await synthesize_to_bytes(reply)
        audio_b64 = base64.b64encode(tts_bytes).decode()

    for sender, content in [("scammer", scammer_text), ("agent", reply)]:
        if content:
            msg = MessageInDB(session_id=session_id, sender=sender, content=content)
            await col_msg.insert_one(msg.model_dump())

    return {
        "transcription": scammer_text,
        "reply":         reply,
        "audio_b64":     audio_b64,
        "intent":        result.get("intent"),
        "strategy":      result.get("strategy"),
    }
