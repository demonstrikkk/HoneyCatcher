"""
Voice API Router
Endpoints for voice upload, transcription, and synthesis.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import logging
import uuid
from datetime import datetime
from pathlib import Path

from core.auth import verify_api_key
from db.mongo import db
from db.models import Session, Message, VoiceChunk
from agents.voice_adapter import voice_adapter
from services.audio_processor import audio_processor
from services.intelligence_extractor import extraction_service
from core.lifecycle import lifecycle_manager

router = APIRouter()
logger = logging.getLogger("api.voice")

class VoiceResponse(BaseModel):
    status: str
    sessionId: str
    transcription: Optional[str] = None
    reply: Optional[str] = None
    naturalizedReply: Optional[str] = None
    audioUrl: Optional[str] = None
    mode: str

async def process_voice_background_tasks(session_id: str, transcription: str):
    """
    Background processing for intelligence extraction from voice.
    """
    if transcription:
        # 1. Extract Intelligence
        await extraction_service.extract(session_id, transcription)
        
        # 2. Check Lifecycle
        await lifecycle_manager.check_termination(session_id)

@router.post("/voice/upload", response_model=VoiceResponse)
async def upload_voice_chunk(
    background_tasks: BackgroundTasks,
    sessionId: str = Form(...),
    audio: UploadFile = File(...),
    mode: str = Form("ai_speaks"),  # ai_speaks | ai_suggests
    sequenceNumber: int = Form(0),
    api_key: str = Depends(verify_api_key)
):
    """
    Receives an audio chunk, transcribes it, runs the agent, and returns voice response.
    """
    try:
        logger.info(f"Received voice chunk for session {sessionId}, seq {sequenceNumber}")
        
        # 1. Read and Validate Session
        session_data = await db.sessions.find_one({"session_id": sessionId})
        if not session_data:
            # Create session if not exists (similar to message.py)
            session = Session(session_id=sessionId, voice_enabled=True, voice_mode=mode)
            await db.sessions.insert_one(session.model_dump())
        else:
            session = Session(**session_data)
            # Update session to voice enabled
            if not session.voice_enabled:
                await db.sessions.update_one(
                    {"session_id": sessionId}, 
                    {"$set": {"voice_enabled": True, "voice_mode": mode}}
                )

        if session.status == "terminated":
            return {
                "status": "terminated",
                "sessionId": sessionId,
                "mode": mode
            }

        # 2. Read Audio Data
        audio_content = await audio.read()
        
        # 3. Process Voice Turn
        # Fetch History for context
        current_history_cursor = db.messages.find({"session_id": sessionId}).sort("timestamp", 1)
        current_history = await current_history_cursor.to_list(length=20)
        formatted_history = [{"role": m["sender"], "content": m["content"]} for m in current_history]

        # Use adapter for the heavy lifting
        result = await voice_adapter.run_voice_turn(
            session_id=sessionId,
            audio_data=audio_content,
            history=formatted_history,
            mode=mode,
            format=audio.filename.split('.')[-1] if '.' in audio.filename else "wav"
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        # 4. Save to DB
        # Save Scammer message
        scammer_msg = Message(
            session_id=sessionId,
            sender="scammer",
            content=result["scammer_transcription"],
            is_voice=True,
            metadata={"confidence": result["scammer_language"]}
        )
        await db.messages.insert_one(scammer_msg.model_dump())

        # Save Agent message
        agent_msg = Message(
            session_id=sessionId,
            sender="agent",
            content=result["agent_reply"],
            is_voice=True,
            speech_naturalized=True,
            audio_file_path=result["agent_audio_path"],
            metadata={"naturalized": result["agent_naturalized"]}
        )
        await db.messages.insert_one(agent_msg.model_dump())

        # Update Session Metrics
        await db.sessions.update_one(
            {"session_id": sessionId},
            {
                "$inc": {"message_count": 2, "audio_chunk_count": 1},
                "$set": {
                    "last_updated": datetime.utcnow(),
                    "detected_language": result["scammer_language"]
                }
            }
        )

        # 5. Background Intelligence Extraction
        background_tasks.add_task(
            process_voice_background_tasks, 
            sessionId, 
            result["scammer_transcription"]
        )

        return {
            "status": "success",
            "sessionId": sessionId,
            "transcription": result["scammer_transcription"],
            "reply": result["agent_reply"],
            "naturalizedReply": result["agent_naturalized"],
            "audioUrl": f"/api/voice/audio/{sessionId}/{Path(result['agent_audio_path']).name}" if result["agent_audio_path"] else None,
            "mode": mode
        }

    except Exception as e:
        logger.error(f"Voice upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voice/audio/{session_id}/{filename}")
async def get_audio_file(session_id: str, filename: str):
    """
    Serve generated audio files for playback.
    """
    from fastapi.responses import FileResponse
    from services.tts_service import tts_service
    
    file_path = tts_service.output_path / session_id / filename
    if not file_path.exists():
        # Check root output path too just in case
        file_path = tts_service.output_path / filename
        
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
        
    return FileResponse(file_path)
