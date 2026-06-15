"""
live_call.py -- WebSocket-based two-way live call with AI coaching.

Endpoint:  ws://<host>/api/live-call/ws/{call_id}?role=operator|scammer
"""

import asyncio
import base64
import io
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from services.stt_service import transcribe_bytes
from services.tts_service import synthesize_to_bytes
from services.intelligence_extractor import extract_entities
from agents.graph import run_agent
from db.mongo import get_collection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/live-call", tags=["live-call"])


def normalize_audio(audio_bytes: bytes, fmt: str = "webm") -> bytes:
    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
        seg = seg.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        return seg.raw_data
    except Exception as e:
        logger.warning("Audio normalisation failed (%s) -- using raw bytes", e)
        return audio_bytes


@dataclass
class AudioBuffer:
    min_bytes: int = 16000 * 2 * 3
    _buf: bytearray = field(default_factory=bytearray)

    def add(self, chunk: bytes) -> None:
        self._buf.extend(chunk)

    def ready(self) -> bool:
        return len(self._buf) >= self.min_bytes

    def flush(self) -> bytes:
        data = bytes(self._buf)
        self._buf.clear()
        return data

    def clear(self) -> None:
        self._buf.clear()


@dataclass
class CallSession:
    call_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

    operator_ws: Optional[WebSocket] = None
    scammer_ws: Optional[WebSocket] = None

    operator_buf: AudioBuffer = field(default_factory=AudioBuffer)
    scammer_buf: AudioBuffer = field(default_factory=AudioBuffer)

    transcript: List[dict] = field(default_factory=list)
    turn_count: int = 0

    @property
    def both_connected(self) -> bool:
        return self.operator_ws is not None and self.scammer_ws is not None

    async def send_operator(self, msg: dict) -> None:
        if self.operator_ws:
            try:
                await self.operator_ws.send_json(msg)
            except Exception:
                pass

    async def send_scammer(self, msg: dict) -> None:
        if self.scammer_ws:
            try:
                await self.scammer_ws.send_json(msg)
            except Exception:
                pass

    async def broadcast(self, msg: dict) -> None:
        await asyncio.gather(
            self.send_operator(msg),
            self.send_scammer(msg),
            return_exceptions=True,
        )

    async def close_all(self) -> None:
        self.is_active = False
        for ws in (self.operator_ws, self.scammer_ws):
            if ws:
                try:
                    await ws.close(code=1000)
                except Exception:
                    pass


class CallManager:
    def __init__(self):
        self._sessions: Dict[str, CallSession] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, call_id: str) -> CallSession:
        async with self._lock:
            if call_id not in self._sessions:
                self._sessions[call_id] = CallSession(call_id=call_id)
            return self._sessions[call_id]

    async def remove(self, call_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(call_id, None)
            if session:
                await session.close_all()

    def get(self, call_id: str) -> Optional[CallSession]:
        return self._sessions.get(call_id)


call_manager = CallManager()


async def _process_transcription(
    session: CallSession,
    speaker: str,
    raw_audio: bytes,
    audio_fmt: str,
) -> Optional[str]:
    buf = session.operator_buf if speaker == "operator" else session.scammer_buf
    pcm = normalize_audio(raw_audio, fmt=audio_fmt)
    buf.add(pcm)

    if not buf.ready():
        return None

    flushed = buf.flush()
    try:
        result = await transcribe_bytes(flushed, fmt="wav")
        text = result.get("text", "").strip()
        if text:
            entry = {
                "speaker": speaker,
                "text": text,
                "language": result.get("language", "en"),
                "confidence": result.get("confidence", 0.95),
                "timestamp": datetime.utcnow().isoformat(),
            }
            session.transcript.append(entry)
            session.turn_count += 1
            return text
    except Exception as e:
        logger.error("Transcription error for %s: %s", speaker, e)

    return None


async def _run_ai_pipeline(session: CallSession, scammer_text: str) -> None:
    intel_task = asyncio.create_task(
        asyncio.to_thread(extract_entities, scammer_text)
    )
    agent_task = asyncio.create_task(
        run_agent(
            scammer_text=scammer_text,
            history=session.transcript[-6:],
            mode="ai_coached",
            turn_count=session.turn_count,
        )
    )

    intel_result, agent_result = await asyncio.gather(
        intel_task, agent_task, return_exceptions=True
    )

    if isinstance(intel_result, dict):
        await session.send_operator({
            "type": "intelligence",
            "entities":    intel_result.get("entities", []),
            "threat_level": intel_result.get("threat_level", 0),
            "tactics":     intel_result.get("tactics", []),
            "timestamp":   datetime.utcnow().isoformat(),
        })

    if isinstance(agent_result, dict) and agent_result.get("coaching_text"):
        coaching_text = agent_result["coaching_text"]

        coaching_audio_b64: Optional[str] = None
        try:
            audio_bytes = await synthesize_to_bytes(coaching_text)
            coaching_audio_b64 = base64.b64encode(audio_bytes).decode()
        except Exception as e:
            logger.warning("TTS failed for coaching: %s", e)

        await session.send_operator({
            "type":          "ai_coaching",
            "text":          coaching_text,
            "audio":         coaching_audio_b64,
            "scripts":       agent_result.get("coaching_scripts", []),
            "strategy":      agent_result.get("strategy", "empathy"),
            "intent":        agent_result.get("intent", "unknown"),
            "timestamp":     datetime.utcnow().isoformat(),
        })


@router.websocket("/ws/{call_id}")
async def live_call_ws(
    websocket: WebSocket,
    call_id: str,
    role: str = Query(..., pattern="^(operator|scammer)$"),
):
    await websocket.accept()
    session = await call_manager.get_or_create(call_id)

    if role == "operator":
        session.operator_ws = websocket
    else:
        session.scammer_ws = websocket

    logger.info("CALL %s: %s connected", call_id, role)

    await websocket.send_json({
        "type":      "connected",
        "role":      role,
        "call_id":   call_id,
        "timestamp": datetime.utcnow().isoformat(),
    })

    if session.both_connected:
        await session.broadcast({
            "type":    "participant_joined",
            "message": "Both participants connected. Call is live.",
        })

    try:
        while session.is_active:
            try:
                msg = await asyncio.wait_for(
                    websocket.receive_json(), timeout=30.0
                )
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "end_call":
                await session.broadcast({
                    "type":      "call_ended",
                    "reason":    "user_request",
                    "duration":  (datetime.utcnow() - session.created_at).seconds,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                await call_manager.remove(call_id)
                return

            if msg_type == "audio":
                raw_b64 = msg.get("data", "")
                audio_fmt = msg.get("format", "webm")
                if not raw_b64:
                    continue

                try:
                    raw_bytes = base64.b64decode(raw_b64)
                except Exception:
                    continue

                relay_target = session.scammer_ws if role == "operator" else session.operator_ws
                if relay_target:
                    asyncio.create_task(relay_target.send_json({
                        "type":      "audio",
                        "data":      raw_b64,
                        "from":      role,
                        "timestamp": datetime.utcnow().isoformat(),
                    }))

                async def _transcribe_and_notify(
                    _raw=raw_bytes, _fmt=audio_fmt, _role=role
                ):
                    text = await _process_transcription(session, _role, _raw, _fmt)
                    if text:
                        await session.broadcast({
                            "type":      "transcription",
                            "speaker":   _role,
                            "text":      text,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        if _role == "scammer" and session.both_connected:
                            asyncio.create_task(_run_ai_pipeline(session, text))

                asyncio.create_task(_transcribe_and_notify())

    except WebSocketDisconnect:
        logger.info("CALL %s: %s disconnected", call_id, role)
    except Exception as e:
        logger.error("CALL %s: %s error: %s", call_id, role, e)
    finally:
        if role == "operator":
            session.operator_ws = None
        else:
            session.scammer_ws = None

        async def _deferred_cleanup():
            await asyncio.sleep(60)
            s = call_manager.get(call_id)
            if s and not s.both_connected:
                logger.info("CALL %s: cleaning up abandoned session", call_id)
                await call_manager.remove(call_id)

        asyncio.create_task(_deferred_cleanup())


class StartCallRequest(BaseModel):
    call_id: Optional[str] = None


@router.post("/start")
async def start_call(req: StartCallRequest):
    call_id = req.call_id or str(uuid.uuid4())
    await call_manager.get_or_create(call_id)
    return {
        "call_id": call_id,
        "operator_url": f"/api/live-call/ws/{call_id}?role=operator",
        "scammer_url":  f"/api/live-call/ws/{call_id}?role=scammer",
    }


@router.get("/status/{call_id}")
async def call_status(call_id: str):
    session = call_manager.get(call_id)
    if not session:
        return {"status": "not_found"}
    return {
        "call_id":           call_id,
        "is_active":         session.is_active,
        "operator_connected": session.operator_ws is not None,
        "scammer_connected":  session.scammer_ws is not None,
        "turn_count":        session.turn_count,
        "created_at":        session.created_at.isoformat(),
    }


@router.post("/end/{call_id}")
async def end_call(call_id: str):
    session = call_manager.get(call_id)
    if session:
        await session.broadcast({"type": "call_ended", "reason": "api_request"})
        await call_manager.remove(call_id)
    return {"status": "ended", "call_id": call_id}
