"""
WebRTC Signaling Server - Real-time P2P Audio Streaming
Handles WebRTC offer/answer exchange and ICE candidate signaling for live calls.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import socketio
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.auth import verify_api_key
from db.mongo import db
from features.live_takeover.streaming_stt import StreamingTranscriber, AudioNormalizer

router = APIRouter()
logger = logging.getLogger("api.webrtc_signaling")

# Socket.IO server for signaling
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False
)

sio_app = socketio.ASGIApp(sio)


# ── Models ────────────────────────────────────────────────────

class WebRTCRoom:
    """Represents a WebRTC call room with two peers."""
    
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.operator_sid: Optional[str] = None
        self.scammer_sid: Optional[str] = None
        self.operator_transcriber = StreamingTranscriber()
        self.scammer_transcriber = StreamingTranscriber()
        self.normalizer = AudioNormalizer()
        self.transcript = []
        self.entities = []
        self.threat_level = 0.0
        self.tactics = []
        self.start_time = datetime.utcnow()
        self.is_active = True
    
    def has_both_peers(self) -> bool:
        return self.operator_sid is not None and self.scammer_sid is not None
    
    def get_peer_sid(self, role: str) -> Optional[str]:
        return self.operator_sid if role == "operator" else self.scammer_sid


class RoomManager:
    """Manages WebRTC rooms and peer connections."""
    
    def __init__(self):
        self.rooms: Dict[str, WebRTCRoom] = {}
        self.sid_to_room: Dict[str, str] = {}
        self.sid_to_role: Dict[str, str] = {}
    
    def create_room(self, room_id: str) -> WebRTCRoom:
        room = WebRTCRoom(room_id)
        self.rooms[room_id] = room
        logger.info(f"📞 WebRTC room created: {room_id}")
        return room
    
    def get_room(self, room_id: str) -> Optional[WebRTCRoom]:
        return self.rooms.get(room_id)
    
    def join_room(self, room_id: str, sid: str, role: str) -> Optional[WebRTCRoom]:
        room = self.rooms.get(room_id)
        if not room:
            room = self.create_room(room_id)
        
        if role == "operator":
            room.operator_sid = sid
        else:
            room.scammer_sid = sid
        
        self.sid_to_room[sid] = room_id
        self.sid_to_role[sid] = role
        
        logger.info(f"👤 {role} joined room {room_id} (sid: {sid})")
        return room
    
    def leave_room(self, sid: str):
        room_id = self.sid_to_room.pop(sid, None)
        role = self.sid_to_role.pop(sid, None)
        
        if room_id:
            room = self.rooms.get(room_id)
            if room:
                if role == "operator":
                    room.operator_sid = None
                else:
                    room.scammer_sid = None
                
                logger.info(f"👤 {role} left room {room_id}")
                
                # Clean up empty rooms
                if not room.has_both_peers():
                    self.rooms.pop(room_id, None)
                    logger.info(f"🧹 Room {room_id} cleaned up")
    
    def get_peer_sid(self, sid: str) -> Optional[str]:
        """Get the other peer's socket ID in the same room."""
        room_id = self.sid_to_room.get(sid)
        if not room_id:
            return None
        
        room = self.rooms.get(room_id)
        if not room:
            return None
        
        role = self.sid_to_role.get(sid)
        if role == "operator":
            return room.scammer_sid
        else:
            return room.operator_sid


room_manager = RoomManager()


# ── Socket.IO Event Handlers ──────────────────────────────────

@sio.event
async def connect(sid, environ):
    """Handle socket connection."""
    logger.info(f"🔌 Client connected: {sid}")
    await sio.emit('connected', {'sid': sid}, room=sid)


@sio.event
async def disconnect(sid):
    """Handle socket disconnection."""
    logger.info(f"🔌 Client disconnected: {sid}")
    
    # Get peer before leaving room
    peer_sid = room_manager.get_peer_sid(sid)
    room_id = room_manager.sid_to_room.get(sid)
    
    # Leave room
    room_manager.leave_room(sid)
    
    # Notify peer
    if peer_sid:
        await sio.emit('peer_disconnected', {'room_id': room_id}, room=peer_sid)


@sio.event
async def join_room(sid, data):
    """
    Join a WebRTC call room.
    
    Args:
        data: {"room_id": "call-xxx", "role": "operator|scammer"}
    """
    room_id = data.get('room_id')
    role = data.get('role', 'operator')
    
    if not room_id:
        await sio.emit('error', {'message': 'room_id required'}, room=sid)
        return
    
    # Join the room
    room = room_manager.join_room(room_id, sid, role)
    await sio.enter_room(sid, room_id)
    
    # Notify user
    await sio.emit('joined_room', {
        'room_id': room_id,
        'role': role,
        'waiting_for_peer': not room.has_both_peers()
    }, room=sid)
    
    # If both peers present, notify both
    if room.has_both_peers():
        await sio.emit('peer_joined', {
            'room_id': room_id,
            'message': 'Both peers connected - ready to exchange WebRTC offers'
        }, room=room_id)
        
        logger.info(f"✅ Room {room_id} has both peers - ready for WebRTC")


@sio.event
async def webrtc_offer(sid, data):
    """
    Forward WebRTC offer to peer.
    
    Args:
        data: {"offer": {"type": "offer", "sdp": "..."}}
    """
    peer_sid = room_manager.get_peer_sid(sid)
    if not peer_sid:
        logger.warning(f"No peer found for {sid}")
        return
    
    logger.info(f"📤 Forwarding WebRTC offer from {sid} to {peer_sid}")
    await sio.emit('webrtc_offer', {
        'offer': data.get('offer'),
        'from': sid
    }, room=peer_sid)


@sio.event
async def webrtc_answer(sid, data):
    """
    Forward WebRTC answer to peer.
    
    Args:
        data: {"answer": {"type": "answer", "sdp": "..."}}
    """
    peer_sid = room_manager.get_peer_sid(sid)
    if not peer_sid:
        logger.warning(f"No peer found for {sid}")
        return
    
    logger.info(f"📤 Forwarding WebRTC answer from {sid} to {peer_sid}")
    await sio.emit('webrtc_answer', {
        'answer': data.get('answer'),
        'from': sid
    }, room=peer_sid)


@sio.event
async def ice_candidate(sid, data):
    """
    Forward ICE candidate to peer.
    
    Args:
        data: {"candidate": {...}}
    """
    peer_sid = room_manager.get_peer_sid(sid)
    if not peer_sid:
        return
    
    logger.debug(f"🧊 Forwarding ICE candidate from {sid} to {peer_sid}")
    await sio.emit('ice_candidate', {
        'candidate': data.get('candidate'),
        'from': sid
    }, room=peer_sid)


@sio.event
async def transcription_chunk(sid, data):
    """
    Receive audio chunk for transcription (sent from frontend via Socket.IO).
    Frontend captures local + remote audio and sends chunks here for STT.
    
    Args:
        data: {"audio": "base64", "format": "webm", "speaker": "operator|scammer", "room_id": "call-xxx"}
    """
    room_id = data.get('room_id') or room_manager.sid_to_room.get(sid)
    speaker = data.get('speaker', 'unknown')
    
    if not room_id:
        logger.warning(f"⚠️ Received audio chunk from {speaker} but no room_id found")
        return
    
    room = room_manager.get_room(room_id)
    if not room:
        logger.warning(f"⚠️ Received audio chunk from {speaker} but room {room_id} not found")
        return
    
    logger.debug(f"📥 Received audio chunk from {speaker} in room {room_id}")
    
    # Process transcription in background
    asyncio.create_task(process_transcription(room, data))


async def process_transcription(room: WebRTCRoom, data: dict):
    """Background task to transcribe audio chunk and extract intelligence."""
    try:
        import base64
        
        speaker = data.get('speaker', 'unknown')
        audio_base64 = data.get('audio')
        audio_format = data.get('format', 'webm')
        
        if not audio_base64:
            logger.warning(f"⚠️ {speaker}: No audio data in chunk")
            return
        
        # Decode audio
        audio_bytes = base64.b64decode(audio_base64)
        logger.debug(f"🎵 {speaker}: Processing {len(audio_bytes)} bytes ({audio_format})")
        
        # Normalize audio chunk to WAV (required by Whisper)
        normalized = room.normalizer.normalize_chunk(audio_bytes, source_format=audio_format)
        
        # Skip if normalization failed (common for incomplete streaming chunks)
        if normalized is None:
            logger.debug(f"⚠️ {speaker}: Normalization failed (incomplete chunk)")
            return
        
        # Get appropriate transcriber
        transcriber = room.scammer_transcriber if speaker == "scammer" else room.operator_transcriber
        
        # Add chunk and check if ready
        chunk_size_kb = len(normalized) / 1024
        logger.debug(f"📊 {speaker}: Added {chunk_size_kb:.1f}KB normalized audio")
        is_ready = transcriber.add_chunk(normalized)
        
        if is_ready:
            logger.info(f"🎙️ {speaker}: Buffer ready, starting transcription...")
            result = await transcriber.transcribe_buffer()
            
            if result and result.get("text"):
                text = result["text"].strip()
                
                # Skip empty or very short transcriptions
                if not text or len(text) < 2:
                    logger.debug(f"⚠️ {speaker}: Skipping empty transcription")
                    return
                
                language = result.get("language", "en")
                confidence = result.get("confidence", 0.0)
                
                # Log language detection
                lang_name = "English" if language == "en" else "Hindi" if language == "hi" else language
                logger.info(f"✅ {speaker}: Transcribed in {lang_name} (confidence: {confidence:.2f})")
                
                transcription = {
                    "speaker": speaker,
                    "text": text,
                    "language": language,
                    "confidence": confidence,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Add to transcript
                room.transcript.append(transcription)
                logger.info(f"📝 {speaker}: '{text[:80]}{'...' if len(text) > 80 else ''}'")
                
                # Send transcription to BOTH operator and scammer
                # (Each can see what they and the other person said)
                await sio.emit('transcription', transcription, room=room.room_id)
                logger.info(f"📤 Sent transcription to room {room.room_id}")
                
                # Save to database
                await db.live_calls.update_one(
                    {"call_id": room.room_id},
                    {"$push": {"transcript": transcription}},
                    upsert=True
                )
                
                # If scammer speaking, extract intelligence and provide AI coaching
                if speaker == "scammer" and room.operator_sid:
                    asyncio.create_task(extract_intelligence(room, result["text"]))
                    asyncio.create_task(provide_ai_coaching(room))
    
    except Exception as e:
        logger.error(f"❌ Transcription error for {data.get('speaker', 'unknown')}: {e}", exc_info=True)


async def extract_intelligence(room: WebRTCRoom, text: str):
    """Extract intelligence from scammer's speech during WebRTC call."""
    try:
        from features.live_takeover.intelligence_pipeline import intelligence_pipeline
        from features.live_takeover.url_scanner import url_scanner
        
        logger.info(f"🧠 Extracting intelligence from: '{text[:100]}...'")
        
        intel_result = await intelligence_pipeline.process_transcript(
            session_id=room.room_id,
            text=text,
            speaker="scammer"
        )
        
        if intel_result.get("new_entities"):
            new_entities = intel_result["new_entities"]
            room.entities.extend(new_entities)
            
            threat_level = intel_result.get("threat_level", 0.0)
            room.threat_level = threat_level
            
            logger.info(f"✅ Extracted {len(new_entities)} entities, threat level: {threat_level:.2f}")
            
            if intel_result.get("tactics"):
                room.tactics.extend(intel_result["tactics"])
                logger.info(f"🎯 Detected tactics: {', '.join(intel_result.get('tactics', []))}")
            
            # Scan URLs if any
            urls_to_scan = intel_result.get("urls_to_scan", [])
            if urls_to_scan:
                logger.info(f"🔗 Scanning {len(urls_to_scan)} URLs with VirusTotal...")
                asyncio.create_task(scan_urls_and_notify(room, urls_to_scan))
            
            # Send intelligence update to operator
            if room.operator_sid:
                await sio.emit('intelligence_update', {
                    "entities": new_entities,
                    "threat_level": threat_level,
                    "tactics": intel_result.get("tactics", []),
                    "timestamp": datetime.utcnow().isoformat()
                }, room=room.operator_sid)
                logger.info(f"📤 Sent intelligence update to operator")
            
            # Update database
            await db.live_calls.update_one(
                {"call_id": room.room_id},
                {
                    "$set": {
                        "entities": room.entities,
                        "threat_level": room.threat_level,
                        "tactics": room.tactics
                    }
                }
            )
    except Exception as e:
        logger.error(f"❌ Intelligence extraction error: {e}", exc_info=True)


async def scan_urls_and_notify(room: WebRTCRoom, urls: list):
    """Scan URLs with VirusTotal and notify operator of results."""
    try:
        from features.live_takeover.url_scanner import url_scanner
        
        logger.info(f"🔍 Starting URL scan for {len(urls)} URLs: {urls}")
        
        results = await url_scanner.scan_urls(urls)
        
        for result in results:
            logger.info(f"🔎 URL Scan Result: {result.url} - {'MALICIOUS' if not result.is_safe else 'SAFE'} (risk: {result.risk_score:.2f})")
            
            # Send to operator
            if room.operator_sid:
                await sio.emit('url_scan_result', {
                    "url": result.url,
                    "is_safe": result.is_safe,
                    "risk_score": result.risk_score,
                    "findings": result.findings,
                    "scanners": result.scanner_results,
                    "timestamp": datetime.utcnow().isoformat()
                }, room=room.operator_sid)
                logger.info(f"📤 Sent URL scan result to operator for {result.url}")
        
        logger.info(f"✅ Completed scanning {len(results)} URLs")
        
    except Exception as e:
        logger.error(f"❌ URL scanning error: {e}", exc_info=True)


async def provide_ai_coaching(room: WebRTCRoom):
    """Generate AI coaching suggestions for operator."""
    try:
        from features.live_takeover.takeover_agent import takeover_agent
        
        # Get recent transcript
        recent = room.transcript[-10:] if len(room.transcript) >= 10 else room.transcript
        transcript_text = "\n".join([f"{t['speaker']}: {t['text']}" for t in recent])
        
        # Get AI coaching (use get_coaching_suggestions for richer context)
        try:
            coaching = await takeover_agent.get_coaching_suggestions(
                conversation=transcript_text,
                entities=room.entities,
                threat_level=room.threat_level,
                tactics=room.tactics
            )
        except AttributeError:
            # Fallback to generate_responses if get_coaching_suggestions not available
            coaching = await takeover_agent.generate_responses(
                transcript=transcript_text,
                entities=room.entities,
                tactics=room.tactics
            )
        
        # Send to operator
        if room.operator_sid:
            await sio.emit('ai_coaching', {
                'suggestions': coaching.get('suggestions', []),
                'recommended_response': coaching.get('recommended_response'),
                'warning': coaching.get('warning'),
                'timestamp': datetime.utcnow().isoformat()
            }, room=room.operator_sid)
    
    except Exception as e:
        logger.error(f"AI coaching error: {e}", exc_info=True)


# ── REST Endpoints (for room creation) ────────────────────────

class CreateRoomRequest(BaseModel):
    operator_name: str = "operator"
    metadata: dict = {}


class CreateRoomResponse(BaseModel):
    room_id: str
    socket_url: str
    status: str


@router.post("/webrtc/room/create", response_model=CreateRoomResponse)
async def create_webrtc_room(
    request: CreateRoomRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create a new WebRTC room for live calling."""
    import uuid
    
    room_id = f"call-{uuid.uuid4().hex[:12]}"
    
    # Create room
    room = room_manager.create_room(room_id)
    
    # Save to database
    await db.live_calls.insert_one({
        "call_id": room_id,
        "operator_name": request.operator_name,
        "metadata": request.metadata,
        "status": "waiting",
        "start_time": datetime.utcnow(),
        "transcript": [],
        "connection_type": "webrtc"
    })
    
    return CreateRoomResponse(
        room_id=room_id,
        socket_url="/socket.io/",
        status="ready"
    )


@router.get("/call/info/{call_id}")
async def get_call_info(
    call_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get WebRTC room info."""
    room = room_manager.get_room(call_id)
    if not room:
        # Try fetching from database for ended calls
        call_doc = await db.live_calls.find_one({"call_id": call_id})
        if not call_doc:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Call not found")
        return {
            "call_id": call_id,
            "operator_name": call_doc.get("operator_name", "Unknown"),
            "status": call_doc.get("status", "inactive"),
            "is_active": False
        }
    
    return {
        "call_id": call_id,
        "operator_name": room_manager.rooms.get(call_id).__dict__.get("operator_name", "Operator"),
        "status": "active",
        "is_active": True,
        "has_both_peers": room.has_both_peers(),
        "start_time": room.start_time.isoformat()
    }


@router.post("/webrtc/room/{room_id}/end")
async def end_webrtc_room(
    room_id: str,
    api_key: str = Depends(verify_api_key)
):
    """End a WebRTC room."""
    room = room_manager.get_room(room_id)
    if room:
        # Notify all participants
        await sio.emit('call_ended', {'room_id': room_id}, room=room_id)
        
        # Update database
        await db.live_calls.update_one(
            {"call_id": room_id},
            {"$set": {"status": "ended", "end_time": datetime.utcnow()}}
        )
    
    return {"message": "Room ended", "room_id": room_id}
