"""
Live Takeover WebSocket API
Real-time bi-directional communication for live scam engagement.
Supports audio streaming, mode switching, and intelligence push.
"""

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

from config import settings
from core.auth import verify_api_key
from db.mongo import db
from features.live_takeover.intelligence_pipeline import intelligence_pipeline
from features.live_takeover.report_generator import report_generator
from features.live_takeover.session_manager import (
    LiveSessionState,
    SessionStatus,
    TakeoverMode,
    live_session_manager,
)
from features.live_takeover.streaming_stt import AudioNormalizer, StreamingTranscriber
from features.live_takeover.takeover_agent import takeover_agent
from features.live_takeover.url_scanner import url_scanner
from features.live_takeover.voice_clone_service import voice_clone_service

router = APIRouter()
logger = logging.getLogger("api.live_takeover")


# ── Connection Manager ────────────────────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections for live sessions."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self.connections[session_id] = ws
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        self.connections.pop(session_id, None)
        logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send(self, session_id: str, data: dict):
        ws = self.connections.get(session_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.error(f"WebSocket send error ({session_id}): {e}")
                self.disconnect(session_id)
    
    async def broadcast_intelligence(self, session_id: str, intel_data: dict):
        """Push intelligence updates to client."""
        await self.send(session_id, {
            "type": "intelligence_update",
            "data": intel_data,
            "timestamp": datetime.utcnow().isoformat()
        })


manager = ConnectionManager()


# ── Request/Response Models ───────────────────────────────────────

class StartSessionRequest(BaseModel):
    original_session_id: Optional[str] = None
    mode: str = "ai_takeover"  # ai_takeover | ai_coached
    voice_clone_id: Optional[str] = None
    language: str = "en"

class StartSessionResponse(BaseModel):
    session_id: str
    status: str
    mode: str
    voice_clone_active: bool

class SwitchModeRequest(BaseModel):
    session_id: str
    new_mode: str  # ai_takeover | ai_coached

class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    mode: str
    turn_count: int
    threat_level: float
    entities_count: int
    duration_seconds: float

class ReportRequest(BaseModel):
    session_id: str
    format: str = "json"  # json | pdf | csv


# ── REST Endpoints ────────────────────────────────────────────────

@router.post("/live/start", response_model=StartSessionResponse)
async def start_live_session(
    req: StartSessionRequest,
    api_key: str = Depends(verify_api_key)
):
    """Start a new live takeover session."""
    try:
        mode = TakeoverMode(req.mode)
    except ValueError:
        raise HTTPException(400, f"Invalid mode: {req.mode}. Use 'ai_takeover' or 'ai_coached'")
    
    session = await live_session_manager.create_session(
        original_session_id=req.original_session_id,
        mode=mode,
        voice_clone_id=req.voice_clone_id,
        language=req.language
    )
    
    voice_active = bool(req.voice_clone_id) and mode == TakeoverMode.AI_TAKEOVER
    
    logger.info(f"Live session started: {session.session_id} (mode={req.mode})")
    
    return StartSessionResponse(
        session_id=session.session_id,
        status="active",
        mode=req.mode,
        voice_clone_active=voice_active
    )


@router.post("/live/switch-mode")
async def switch_mode(
    req: SwitchModeRequest,
    api_key: str = Depends(verify_api_key)
):
    """Switch between AI takeover and AI coached mode."""
    try:
        new_mode = TakeoverMode(req.new_mode)
    except ValueError:
        raise HTTPException(400, f"Invalid mode: {req.new_mode}")
    
    success = await live_session_manager.switch_mode(req.session_id, new_mode)
    
    if not success:
        raise HTTPException(404, f"Session {req.session_id} not found")
    
    # Notify via WebSocket
    await manager.send(req.session_id, {
        "type": "mode_switched",
        "new_mode": req.new_mode,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"status": "ok", "new_mode": req.new_mode}


@router.get("/live/status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get current session status."""
    session = await live_session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")
    
    duration = (datetime.utcnow() - session.started_at).total_seconds()
    
    return SessionStatusResponse(
        session_id=session.session_id,
        status=session.status.value,
        mode=session.current_mode.value,
        turn_count=session.turn_count,
        threat_level=session.threat_level,
        entities_count=len(session.extracted_entities),
        duration_seconds=duration
    )


@router.post("/live/end/{session_id}")
async def end_live_session(
    session_id: str,
    api_key: str = Depends(verify_api_key)
):
    """End a live takeover session."""
    success = await live_session_manager.end_session(session_id)
    
    if not success:
        raise HTTPException(404, f"Session {session_id} not found")
    
    # Notify via WebSocket
    await manager.send(session_id, {
        "type": "session_ended",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    manager.disconnect(session_id)
    
    return {"status": "ended", "session_id": session_id}


@router.post("/live/report")
async def generate_report(
    req: ReportRequest,
    api_key: str = Depends(verify_api_key)
):
    """Generate report for a session."""
    try:
        result = await report_generator.generate_report(
            session_id=req.session_id,
            format=req.format
        )
        
        if req.format in ("pdf", "csv"):
            file_path = result.get("file_path")
            if file_path:
                return FileResponse(
                    file_path,
                    media_type="application/octet-stream",
                    filename=f"{result['report_id']}.{req.format}"
                )
        
        return result
        
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        raise HTTPException(500, "Report generation failed")


@router.post("/live/report/all/{session_id}")
async def generate_all_reports(
    session_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Generate reports in all formats."""
    try:
        results = await report_generator.generate_all_formats(session_id)
        return {"status": "ok", "reports": results}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── WebSocket Endpoint ────────────────────────────────────────────

@router.websocket("/live/connect/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket connection for real-time live takeover.
    
    Client → Server messages:
        {"type": "audio_chunk", "data": "<base64>", "format": "wav"}
        {"type": "mode_switch", "mode": "ai_coached"}
        {"type": "text_input", "text": "..."}  # manual text in coached mode
        
    Server → Client messages:
        {"type": "transcription", "text": "...", "speaker": "scammer"}
        {"type": "ai_response", "text": "...", "audio": "<base64>"}     # ai_takeover
        {"type": "coaching_scripts", "scripts": [...]}                    # ai_coached
        {"type": "intelligence_update", "data": {...}}
        {"type": "threat_update", "level": 0.7, "tactics": [...]}
        {"type": "url_scan_result", "data": {...}}
        {"type": "mode_switched", "new_mode": "..."}
        {"type": "error", "message": "..."}
        {"type": "session_ended"}
    """
    session_maybe = await live_session_manager.get_session(session_id)
    
    if not session_maybe:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    # Type narrowing: session is guaranteed not None after this point
    session: LiveSessionState = session_maybe
    
    await manager.connect(session_id, websocket)
    
    # Create streaming transcriber for this session
    transcriber = StreamingTranscriber(buffer_threshold_ms=2500)
    normalizer = AudioNormalizer()
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "mode": session.current_mode.value,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            raw_message = await websocket.receive_text()
            
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                continue
            
            msg_type = message.get("type", "")
            
            # ── Audio Chunk Processing ────────────────────
            if msg_type == "audio_chunk":
                await _handle_audio_chunk(
                    websocket, session_id, session,
                    message, transcriber, normalizer
                )
            
            # ── Mode Switch ───────────────────────────────
            elif msg_type == "mode_switch":
                new_mode_str = message.get("mode", "")
                try:
                    new_mode = TakeoverMode(new_mode_str)
                    await live_session_manager.switch_mode(session_id, new_mode)
                    updated_session = await live_session_manager.get_session(session_id)
                    
                    if updated_session:
                        updated_session.transcript.append({
                            "speaker": "system",
                            "text": f"Mode switched to {new_mode_str}",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        updated_session.turn_count += 1
                        # Update the main session reference
                        session = updated_session
                    
                    await websocket.send_json({
                        "type": "mode_switched",
                        "new_mode": new_mode_str,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except ValueError:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Invalid mode: {new_mode_str}"
                    })
            
            # ── Text Input (coached mode) ─────────────────
            elif msg_type == "text_input":
                text = message.get("text", "")
                if text:
                    # Add to transcript as user-narrated
                    session.transcript.append({
                        "speaker": "agent",
                        "text": text,
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "user_narrated"
                    })
                    session.turn_count += 1
            
            # ── Ping/Keep-alive ───────────────────────────
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error ({session_id}): {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Internal server error"
            })
        except:
            pass
    finally:
        manager.disconnect(session_id)


async def _handle_audio_chunk(
    websocket: WebSocket,
    session_id: str,
    session: "LiveSessionState",
    message: dict,
    transcriber: StreamingTranscriber,
    normalizer: AudioNormalizer
):
    """Process an incoming audio chunk through the full pipeline."""
    try:
        # Decode audio
        audio_b64 = message.get("data", "")
        audio_format = message.get("format", "wav")
        
        audio_bytes = base64.b64decode(audio_b64)
        
        # Normalize audio
        normalized = normalizer.normalize_chunk(audio_bytes, audio_format)
        if not normalized:
            return
        
        # Buffer and transcribe
        is_ready = transcriber.add_chunk(normalized)
        
        if not is_ready:
            return  # Not enough audio buffered yet
        
        # Transcribe the buffer
        transcription = await transcriber.transcribe_buffer()
        if not transcription:
            return  # Transcription failed
        
        scammer_text = transcription["text"]
        
        # ── Push transcription to client ──────────────────
        await websocket.send_json({
            "type": "transcription",
            "text": scammer_text,
            "speaker": "scammer",
            "language": transcription.get("language", "en"),
            "confidence": transcription.get("confidence", 0.0),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Add to transcript
        session.transcript.append({
            "speaker": "scammer",
            "text": scammer_text,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # ── Intelligence extraction (parallel) ────────────
        intel_callback = lambda data: manager.broadcast_intelligence(session_id, data)
        
        intel_task = asyncio.create_task(
            intelligence_pipeline.process_transcript(
                session_id=session_id,
                text=scammer_text,
                speaker="scammer",
                notify_callback=intel_callback
            )
        )
        
        # ── Agent processing ──────────────────────────────
        # Build history from transcript
        history = [
            {"role": t["speaker"], "content": t["text"]}
            for t in session.transcript[-20:]
        ]
        
        agent_result = await takeover_agent.run(
            scammer_text=scammer_text,
            history=history,
            mode=session.current_mode.value,
            language=session.detected_language,
            turn_count=session.turn_count
        )
        
        # Wait for intelligence extraction
        intel_result = await intel_task
        
        # ── URL scanning (if new URLs found) ──────────────
        urls_to_scan = intel_result.get("urls_to_scan", [])
        if urls_to_scan:
            asyncio.create_task(
                _scan_and_notify(websocket, session_id, session, urls_to_scan)
            )
        
        # ── Process agent extracted data ──────────────────
        extracted = agent_result.get("extracted_data", {})
        if extracted:
            await intelligence_pipeline.process_agent_extracted(
                session_id=session_id,
                extracted_data=extracted,
                notify_callback=intel_callback
            )
        
        # ── Send response based on mode ───────────────────
        if session.current_mode == TakeoverMode.AI_TAKEOVER:
            response_text = agent_result.get("response", "")
            
            # Add to transcript
            session.transcript.append({
                "speaker": "agent",
                "text": response_text,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "ai_takeover"
            })
            
            # Synthesize voice - use voice clone if available, otherwise ElevenLabs
            audio_result = None
            audio_bytes = None
            if session.voice_clone_id:
                try:
                    audio_result = await voice_clone_service.synthesize(
                        text=response_text,
                        voice_id=session.voice_clone_id
                    )
                    audio_bytes = audio_result["audio_data"] if audio_result else None
                except Exception as e:
                    logger.error(f"Voice clone synthesis error: {e}")
            
            # Fallback to ElevenLabs default voices if no clone or clone failed
            if audio_bytes is None:
                try:
                    from services.elevenlabs_service import elevenlabs_service
                    from services.tts_service import tts_service
                    el_audio = await tts_service.synthesize_to_bytes(
                        text=response_text,
                        voice_id=getattr(settings, 'ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
                    )
                    if el_audio:
                        audio_bytes = el_audio
                        logger.info("✅ ElevenLabs fallback TTS used for ai_takeover response")
                    else:
                        logger.warning("ElevenLabs fallback returned no audio")
                except Exception as el_err:
                    logger.warning(f"ElevenLabs fallback TTS failed: {el_err}")
            
            await websocket.send_json({
                "type": "ai_response",
                "text": response_text,
                "audio": base64.b64encode(audio_bytes).decode() if audio_bytes else None,
                "strategy": agent_result.get("strategy", ""),
                "threat_level": intel_result.get("threat_level", 0),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        elif session.current_mode == TakeoverMode.AI_COACHED:
            scripts = agent_result.get("scripts", [])
            
            await websocket.send_json({
                "type": "coaching_scripts",
                "scripts": scripts,
                "strategy": agent_result.get("strategy", ""),
                "intent": agent_result.get("intent", ""),
                "emotion": agent_result.get("emotion", ""),
                "threat_level": intel_result.get("threat_level", 0),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # ── Send threat update ────────────────────────────
        await websocket.send_json({
            "type": "threat_update",
            "level": intel_result.get("threat_level", 0),
            "tactics": intel_result.get("tactics", []),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        session.turn_count += 1
        
    except Exception as e:
        logger.error(f"Audio chunk processing error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Processing error: {str(e)}"
        })


async def _scan_and_notify(
    websocket: WebSocket,
    session_id: str,
    session: "LiveSessionState",
    urls: List[str]
):
    """Scan URLs and push results to client."""
    try:
        results = await url_scanner.scan_urls(urls)
        
        for result in results:
            session.url_scan_results.append(result)
            
            await websocket.send_json({
                "type": "url_scan_result",
                "data": {
                    "url": result.url,
                    "is_safe": result.is_safe,
                    "risk_score": result.risk_score,
                    "findings": result.findings
                },
                "timestamp": datetime.utcnow().isoformat()
            })
    except Exception as e:
        logger.error(f"URL scan error: {e}")
