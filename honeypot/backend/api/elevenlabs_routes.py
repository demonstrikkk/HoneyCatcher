"""
ElevenLabs API Endpoints - Voice Management and TTS
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import verify_api_key
from services.elevenlabs_service import elevenlabs_service

router = APIRouter()
logger = logging.getLogger("api.elevenlabs")


# ── Models ────────────────────────────────────────────────────

class SynthesizeRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    voice_name: Optional[str] = None
    session_id: Optional[str] = None
    model: Optional[str] = None
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


class SynthesizeResponse(BaseModel):
    audio_path: str
    duration: float
    format: str
    voice_id: Optional[str]
    voice_name: Optional[str]
    error: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/elevenlabs/voices")
async def get_voices(api_key: str = Depends(verify_api_key)):
    """
    Get list of available ElevenLabs voices.
    Returns all free voices even without API key.
    
    GET /api/elevenlabs/voices
    
    Returns:
        {
            "voices": [
                {
                    "voice_id": "...",
                    "name": "Rachel",
                    "labels": {...},
                    "category": "premade",
                    "description": "Rachel - Natural female voice"
                },
                ...
            ]
        }
    """
    try:
        voices = await elevenlabs_service.get_available_voices()
        return {"voices": voices, "count": len(voices)}
    except Exception as e:
        logger.error(f"Failed to fetch voices: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e))


@router.post("/elevenlabs/synthesize", response_model=SynthesizeResponse)
async def synthesize_speech(
    request: SynthesizeRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Synthesize speech from text using ElevenLabs.
    
    POST /api/elevenlabs/synthesize
    Body:
        {
            "text": "Hello world",
            "voice_name": "Rachel",  // or voice_id
            "session_id": "optional-session-id",
            "model": "eleven_turbo_v2_5",
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": true
        }
    
    Returns:
        {
            "audio_path": "/path/to/audio.mp3",
            "duration": 3.5,
            "format": "mp3",
            "voice_id": "...",
            "voice_name": "Rachel"
        }
    """
    try:
        result = await elevenlabs_service.synthesize(
            text=request.text,
            voice_id=request.voice_id,
            voice_name=request.voice_name,
            session_id=request.session_id,
            model=request.model,
            stability=request.stability,
            similarity_boost=request.similarity_boost,
            style=request.style,
            use_speaker_boost=request.use_speaker_boost
        )
        
        return SynthesizeResponse(**result)
    
    except Exception as e:
        logger.error(f"Speech synthesis failed: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e))


@router.get("/elevenlabs/test")
async def test_elevenlabs(
    text: str = "Hello! This is a test of ElevenLabs text to speech.",
    voice_name: str = "Rachel",
    api_key: str = Depends(verify_api_key)
):
    """
    Test ElevenLabs TTS service.
    
    GET /api/elevenlabs/test?text=Hello&voice_name=Rachel
    
    Returns synthesized audio result.
    """
    try:
        result = await elevenlabs_service.synthesize(
            text=text,
            voice_name=voice_name
        )
        
        return {
            "status": "success",
            "message": f"Successfully synthesized using {voice_name}",
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }
