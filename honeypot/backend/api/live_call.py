"""
Live Call API - Real-time Two-Way Voice Communication
Enables real-time voice calls between scammer and operator with AI assistance.
"""

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel

from core.auth import verify_api_key
from db.mongo import db
from features.live_takeover.intelligence_pipeline import intelligence_pipeline
from features.live_takeover.report_generator import report_generator
from features.live_takeover.streaming_stt import StreamingTranscriber, AudioNormalizer
from features.live_takeover.takeover_agent import takeover_agent
from services.elevenlabs_service import elevenlabs_service

router = APIRouter()
logger = logging.getLogger("api.live_call")


# ── Models ────────────────────────────────────────────────────

class CallSession:
    """Represents an active two-way call session."""
    
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.operator_ws: Optional[WebSocket] = None
        self.scammer_ws: Optional[WebSocket] = None
        self.operator_transcriber = StreamingTranscriber()
        self.scammer_transcriber = StreamingTranscriber()
        self.normalizer = AudioNormalizer()
        self.transcript = []
        self.entities = []
        self.threat_level = 0.0
        self.tactics = []
        self.start_time = datetime.utcnow()
        self.is_active = True
        
    def has_both_participants(self) -> bool:
        return self.operator_ws is not None and self.scammer_ws is not None
    
    async def close_all(self):
        """Close all connections gracefully."""
        self.is_active = False
        if self.operator_ws:
            try:
                await self.operator_ws.close()
            except:
                pass
        if self.scammer_ws:
            try:
                await self.scammer_ws.close()
            except:
                pass


class CallManager:
    """Manages active call sessions and audio routing."""
    
    def __init__(self):
        self.sessions: Dict[str, CallSession] = {}
        self.operator_to_call: Dict[WebSocket, str] = {}
        self.scammer_to_call: Dict[WebSocket, str] = {}
    
    def create_session(self, call_id: str) -> CallSession:
        """Create a new call session."""
        session = CallSession(call_id)
        self.sessions[call_id] = session
        logger.info(f"📞 Call session created: {call_id}")
        return session
    
    def get_session(self, call_id: str) -> Optional[CallSession]:
        """Get existing call session."""
        return self.sessions.get(call_id)
    
    async def connect_operator(self, call_id: str, ws: WebSocket) -> CallSession:
        """Connect operator to call session."""
        session = self.sessions.get(call_id)
        if not session:
            session = self.create_session(call_id)
        
        await ws.accept()
        session.operator_ws = ws
        self.operator_to_call[ws] = call_id
        logger.info(f"🎧 Operator connected to call: {call_id}")
        
        # Notify operator
        await self.send_to_operator(call_id, {
            "type": "connected",
            "role": "operator",
            "call_id": call_id,
            "waiting_for_scammer": session.scammer_ws is None
        })
        
        return session
    
    async def connect_scammer(self, call_id: str, ws: WebSocket) -> CallSession:
        """Connect scammer to call session."""
        session = self.sessions.get(call_id)
        if not session:
            session = self.create_session(call_id)
        
        await ws.accept()
        session.scammer_ws = ws
        self.scammer_to_call[ws] = call_id
        logger.info(f"📱 Scammer connected to call: {call_id}")
        
        # Notify scammer
        await self.send_to_scammer(call_id, {
            "type": "connected",
            "role": "scammer",
            "call_id": call_id
        })
        
        # Notify operator that scammer joined
        if session.operator_ws:
            await self.send_to_operator(call_id, {
                "type": "participant_joined",
                "role": "scammer",
                "message": "Scammer has joined the call"
            })
        
        return session
    
    def disconnect_operator(self, ws: WebSocket):
        """Handle operator disconnect."""
        call_id = self.operator_to_call.pop(ws, None)
        if call_id:
            session = self.sessions.get(call_id)
            if session:
                session.operator_ws = None
                logger.info(f"🎧❌ Operator disconnected: {call_id}")
    
    def disconnect_scammer(self, ws: WebSocket):
        """Handle scammer disconnect."""
        call_id = self.scammer_to_call.pop(ws, None)
        if call_id:
            session = self.sessions.get(call_id)
            if session:
                session.scammer_ws = None
                logger.info(f"📱❌ Scammer disconnected: {call_id}")
    
    async def send_to_operator(self, call_id: str, data: dict):
        """Send message to operator."""
        session = self.sessions.get(call_id)
        if session and session.operator_ws:
            try:
                await session.operator_ws.send_json(data)
            except Exception as e:
                logger.error(f"Error sending to operator: {e}")
    
    async def send_to_scammer(self, call_id: str, data: dict):
        """Send message to scammer."""
        session = self.sessions.get(call_id)
        if session and session.scammer_ws:
            try:
                await session.scammer_ws.send_json(data)
            except Exception as e:
                logger.error(f"Error sending to scammer: {e}")
    
    async def route_audio_to_scammer(self, call_id: str, audio_base64: str, format: str = "webm"):
        """Route operator's audio to scammer (with conversion to playable format)."""
        session = self.sessions.get(call_id)
        if not session:
            return
        
        try:
            # Decode and normalize audio to make it playable
            audio_bytes = base64.b64decode(audio_base64)
            normalized = session.normalizer.normalize_chunk(audio_bytes, source_format=format)
            
            if normalized:
                # Re-encode to base64 and send as WAV (more compatible)
                normalized_base64 = base64.b64encode(normalized).decode('utf-8')
                await self.send_to_scammer(call_id, {
                    "type": "audio_stream",
                    "audio": normalized_base64,
                    "format": "wav",  # Normalized audio is WAV format
                    "source": "operator",
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                # Skip if normalization failed (incomplete chunk)
                logger.debug(f"Skipped audio routing (normalization failed)")
        except Exception as e:
            logger.error(f"Audio routing error: {e}")
    
    async def route_audio_to_operator(self, call_id: str, audio_base64: str, format: str = "webm"):
        """Route scammer's audio to operator (with conversion to playable format)."""
        session = self.sessions.get(call_id)
        if not session:
            return
        
        try:
            # Decode and normalize audio to make it playable
            audio_bytes = base64.b64decode(audio_base64)
            normalized = session.normalizer.normalize_chunk(audio_bytes, source_format=format)
            
            if normalized:
                # Re-encode to base64 and send as WAV (more compatible)
                normalized_base64 = base64.b64encode(normalized).decode('utf-8')
                await self.send_to_operator(call_id, {
                    "type": "audio_stream",
                    "audio": normalized_base64,
                    "format": "wav",  # Normalized audio is WAV format
                    "source": "scammer",
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                # Skip if normalization failed (incomplete chunk)
                logger.debug(f"Skipped audio routing (normalization failed)")
        except Exception as e:
            logger.error(f"Audio routing error: {e}")
    
    async def cleanup_session(self, call_id: str):
        """Clean up ended call session."""
        session = self.sessions.pop(call_id, None)
        if session:
            await session.close_all()
            logger.info(f"🧹 Call session cleaned up: {call_id}")


call_manager = CallManager()


# ── REST Endpoints ────────────────────────────────────────────

class StartCallRequest(BaseModel):
    operator_name: Optional[str] = "Operator"
    metadata: Optional[dict] = {}

class StartCallResponse(BaseModel):
    call_id: str
    operator_link: str
    scammer_link: str
    status: str

@router.post("/call/start", response_model=StartCallResponse)
async def start_call(
    request: StartCallRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Initialize a new call session.
    Returns links for both operator and scammer to join.
    """
    call_id = f"call-{uuid.uuid4().hex[:12]}"
    
    # Create session in manager
    session = call_manager.create_session(call_id)
    
    # Save to database
    await db.live_calls.insert_one({
        "call_id": call_id,
        "operator_name": request.operator_name,
        "metadata": request.metadata,
        "status": "waiting",
        "start_time": datetime.utcnow(),
        "transcript": [],
        "entities": [],
        "threat_level": 0.0
    })
    
    return StartCallResponse(
        call_id=call_id,
        operator_link=f"/api/call/connect?call_id={call_id}&role=operator",
        scammer_link=f"/api/call/connect?call_id={call_id}&role=scammer",
        status="ready"
    )


@router.post("/call/end/{call_id}")
async def end_call(
    call_id: str,
    api_key: str = Depends(verify_api_key)
):
    """End an active call and generate report."""
    session = call_manager.get_session(call_id)
    if not session:
        raise HTTPException(404, "Call not found")
    
    # Mark as ended
    session.is_active = False
    
    # Update database
    await db.live_calls.update_one(
        {"call_id": call_id},
        {
            "$set": {
                "status": "ended",
                "end_time": datetime.utcnow(),
                "transcript": session.transcript,
                "entities": session.entities,
                "threat_level": session.threat_level,
                "tactics": session.tactics
            }
        }
    )
    
    # Notify both participants
    await call_manager.send_to_operator(call_id, {"type": "call_ended"})
    await call_manager.send_to_scammer(call_id, {"type": "call_ended"})
    
    # Cleanup
    await call_manager.cleanup_session(call_id)
    
    return {"status": "ended", "call_id": call_id}


@router.get("/call/report/{call_id}")
async def get_call_report(
    call_id: str,
    format: str = "json",
    api_key: str = Depends(verify_api_key)
):
    """Generate detailed report from call session."""
    call_data = await db.live_calls.find_one({"call_id": call_id})
    if not call_data:
        raise HTTPException(404, "Call not found")
    
    if format == "pdf":
        # Generate PDF report
        pdf_result = await report_generator.generate_report(session_id=call_id, format="pdf")
        
        from fastapi.responses import FileResponse
        if pdf_result.get("file_path"):
            return FileResponse(
                pdf_result["file_path"],
                media_type="application/pdf",
                filename=f"call_report_{call_id}.pdf"
            )
        else:
            # Fallback to JSON if PDF failed
            return pdf_result
    
    # Return JSON report
    return {
        "call_id": call_id,
        "status": call_data.get("status"),
        "duration": (call_data.get("end_time", datetime.utcnow()) - call_data["start_time"]).total_seconds(),
        "transcript": call_data.get("transcript", []),
        "entities": call_data.get("entities", []),
        "threat_level": call_data.get("threat_level", 0),
        "tactics": call_data.get("tactics", []),
        "summary": f"Call involved {len(call_data.get('transcript', []))} messages"
    }


# ── WebSocket Endpoints ───────────────────────────────────────

@router.websocket("/call/connect")
async def websocket_call_endpoint(
    websocket: WebSocket,
    call_id: str,
    role: str  # "operator" or "scammer"
):
    """
    WebSocket endpoint for real-time two-way voice calls.
    
    Messages from client:
        {"type": "audio_chunk", "audio": "<base64>", "format": "webm"}
        {"type": "text_message", "text": "..."} (chat fallback)
        {"type": "ping"}
    
    Messages to operator:
        {"type": "audio_stream", "audio": "<base64>", "source": "scammer"}
        {"type": "transcription", "text": "...", "speaker": "scammer", "language": "en"}
        {"type": "ai_coaching", "suggestions": [...]}
        {"type": "intelligence_update", "entities": [...], "threat_level": 0.7}
        {"type": "participant_joined", "role": "scammer"}
        {"type": "call_ended"}
    
    Messages to scammer:
        {"type": "audio_stream", "audio": "<base64>", "source": "operator"}
        {"type": "call_ended"}
    """
    
    if role not in ["operator", "scammer"]:
        await websocket.close(code=4000, reason="Invalid role")
        return
    
    # Connect based on role
    try:
        if role == "operator":
            session = await call_manager.connect_operator(call_id, websocket)
        else:
            session = await call_manager.connect_scammer(call_id, websocket)
        
        # Main message loop
        while session.is_active:
            try:
                data = await websocket.receive_json()
                await handle_call_message(call_id, role, data, session)
            
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {role} in {call_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket error ({role}): {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
    
    finally:
        # Cleanup on disconnect
        if role == "operator":
            call_manager.disconnect_operator(websocket)
            # Notify scammer
            await call_manager.send_to_scammer(call_id, {
                "type": "participant_left",
                "role": "operator"
            })
        else:
            call_manager.disconnect_scammer(websocket)
            # Notify operator
            await call_manager.send_to_operator(call_id, {
                "type": "participant_left",
                "role": "scammer"
            })


async def handle_call_message(call_id: str, role: str, data: dict, session: CallSession):
    """Handle incoming WebSocket message."""
    msg_type = data.get("type")
    
    if msg_type == "audio_chunk":
        await handle_audio_chunk(call_id, role, data, session)
    
    elif msg_type == "text_message":
        await handle_text_message(call_id, role, data, session)
    
    elif msg_type == "ping":
        # Respond with pong
        if role == "operator":
            await call_manager.send_to_operator(call_id, {"type": "pong"})
        else:
            await call_manager.send_to_scammer(call_id, {"type": "pong"})
    
    elif msg_type == "request_coaching":
        # Operator requests AI coaching based on current context
        if role == "operator":
            await provide_ai_coaching(call_id, session)


async def handle_audio_chunk(call_id: str, role: str, data: dict, session: CallSession):
    """
    Handle audio chunk from participant.
    1. Route audio to other participant
    2. Transcribe (for intelligence if from scammer, for transcript if from operator)
    3. Extract intelligence if from scammer
    4. Provide AI coaching if from scammer (to help operator)
    """
    audio_base64 = data.get("audio", "")
    audio_format = data.get("format", "webm")
    
    if not audio_base64:
        return
    
    # 1. Route audio to other participant
    if role == "operator":
        # Operator speaking → send to scammer
        await call_manager.route_audio_to_scammer(call_id, audio_base64, audio_format)
    else:
        # Scammer speaking → send to operator
        await call_manager.route_audio_to_operator(call_id, audio_base64, audio_format)
    
    # 2. Transcribe audio (async background)
    asyncio.create_task(transcribe_and_analyze(call_id, role, audio_base64, audio_format, session))


async def transcribe_and_analyze(call_id: str, role: str, audio_base64: str, audio_format: str, session: CallSession):
    """
    Background task: Transcribe audio and analyze intelligence.
    """
    try:
        # Decode audio
        audio_bytes = base64.b64decode(audio_base64)
        
        # Normalize audio chunk
        normalized = session.normalizer.normalize_chunk(audio_bytes, source_format=audio_format)
        
        # Skip if normalization failed (common for streaming WebM chunks)
        if normalized is None:
            return
        
        # Transcribe
        transcriber = session.scammer_transcriber if role == "scammer" else session.operator_transcriber
        is_ready = transcriber.add_chunk(normalized)
        
        if is_ready:
            result = await transcriber.transcribe_buffer()
            
            if result and result.get("text"):
                transcription = {
                    "speaker": role,
                    "text": result["text"],
                    "language": result.get("language", "en"),
                    "confidence": result.get("confidence", 0.0),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Add to transcript
                session.transcript.append(transcription)
                
                # Send transcription to operator
                await call_manager.send_to_operator(call_id, {
                    "type": "transcription",
                    **transcription
                })
                
                # Save to database
                await db.live_calls.update_one(
                    {"call_id": call_id},
                    {"$push": {"transcript": transcription}}
                )
                
                # If scammer is speaking, extract intelligence and provide AI coaching
                if role == "scammer":
                    await extract_intelligence(call_id, result["text"], session)
                    await provide_ai_coaching(call_id, session)
    
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)


async def extract_intelligence(call_id: str, text: str, session: CallSession):
    """Extract intelligence from scammer's speech."""
    try:
        # Use intelligence pipeline to extract entities
        intel_result = await intelligence_pipeline.process_transcript(
            session_id=call_id,
            text=text,
            speaker="scammer"
        )
        
        if intel_result.get("new_entities"):
            new_entities = intel_result["new_entities"]
            session.entities.extend(new_entities)
            
            # Get threat level from result
            threat_level = intel_result.get("threat_level", 0.0)
            session.threat_level = threat_level
            
            # Detect tactics
            if intel_result.get("tactics"):
                session.tactics.extend(intel_result["tactics"])
            
            # Send intelligence update to operator
            await call_manager.send_to_operator(call_id, {
                "type": "intelligence_update",
                "entities": new_entities,
                "threat_level": threat_level,
                "tactics": intel_result.get("tactics", []),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update database
            await db.live_calls.update_one(
                {"call_id": call_id},
                {
                    "$set": {
                        "entities": session.entities,
                        "threat_level": session.threat_level,
                        "tactics": session.tactics
                    }
                }
            )
    
    except Exception as e:
        logger.error(f"Intelligence extraction error: {e}", exc_info=True)


async def provide_ai_coaching(call_id: str, session: CallSession):
    """
    Provide AI coaching suggestions to operator based on conversation context.
    Also generates AI voice response using ElevenLabs if needed.
    """
    try:
        # Get recent conversation context
        recent_transcript = session.transcript[-10:] if len(session.transcript) > 10 else session.transcript
        
        # Format conversation for AI
        conversation = "\n".join([
            f"{msg['speaker']}: {msg['text']}"
            for msg in recent_transcript
        ])
        
        # Get AI coaching from takeover agent
        coaching = await takeover_agent.get_coaching_suggestions(
            conversation=conversation,
            entities=session.entities,
            threat_level=session.threat_level,
            tactics=session.tactics
        )
        
        # Optionally generate AI voice for recommended response
        audio_data = None
        if coaching.get("recommended_response"):
            try:
                # Use ElevenLabs to synthesize the AI response
                voice_name = getattr(settings, 'ELEVENLABS_DEFAULT_VOICE', 'Rachel')
                audio_result = await elevenlabs_service.synthesize(
                    text=coaching["recommended_response"],
                    voice_name=voice_name,
                    session_id=call_id
                )
                
                if audio_result.get("audio_path") and not audio_result.get("error"):
                    # Use local_path for reading file bytes (audio_path may be Cloudinary URL)
                    local_path = audio_result.get("local_path") or audio_result.get("audio_path")
                    
                    # Check if it's a local file we can read
                    from pathlib import Path as FilePath
                    if local_path and not local_path.startswith("http") and FilePath(local_path).exists():
                        with open(local_path, 'rb') as f:
                            audio_bytes = f.read()
                            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                            audio_data = {
                                "audio_base64": audio_base64,
                                "format": "mp3",
                                "duration": audio_result.get("duration", 0)
                            }
                    elif local_path and local_path.startswith("http"):
                        # If it's a Cloudinary URL, download and convert to base64
                        try:
                            import httpx
                            async with httpx.AsyncClient() as http_client:
                                resp = await http_client.get(local_path, timeout=15.0)
                                if resp.status_code == 200:
                                    audio_base64 = base64.b64encode(resp.content).decode('utf-8')
                                    audio_data = {
                                        "audio_base64": audio_base64,
                                        "format": "mp3",
                                        "duration": audio_result.get("duration", 0)
                                    }
                        except Exception as dl_err:
                            logger.warning(f"Failed to download audio from URL: {dl_err}")
                    
                    logger.info(f"✅ Generated AI voice using ElevenLabs ({voice_name})")
            except Exception as voice_error:
                logger.warning(f"AI voice generation failed: {voice_error}")
        
        # Send coaching to operator
        await call_manager.send_to_operator(call_id, {
            "type": "ai_coaching",
            "intent": coaching.get("intent", "Unknown"),
            "confidence": coaching.get("confidence", 0.0),
            "reasoning": coaching.get("reasoning", ""),
            "suggestions": coaching.get("suggestions", []),
            "recommended_response": coaching.get("recommended_response"),
            "recommended_audio": audio_data,
            "warning": coaching.get("warning"),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"AI coaching error: {e}", exc_info=True)


async def handle_text_message(call_id: str, role: str, data: dict, session: CallSession):
    """Handle text-based message (chat fallback)."""
    text = data.get("text", "")
    if not text:
        return
    
    message = {
        "speaker": role,
        "text": text,
        "type": "text",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    session.transcript.append(message)
    
    # Notify other participant
    if role == "operator":
        await call_manager.send_to_scammer(call_id, {
            "type": "text_message",
            "text": text,
            "from": "operator"
        })
    else:
        await call_manager.send_to_operator(call_id, {
            "type": "text_message",
            "text": text,
            "from": "scammer"
        })
        
        # Extract intelligence from scammer's text
        await extract_intelligence(call_id, text, session)
        await provide_ai_coaching(call_id, session)
