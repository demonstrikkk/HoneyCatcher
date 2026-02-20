"""
Voice Clone Service - ElevenLabs Integration
Handles voice cloning, TTS synthesis with cloned voice, and voice profile management.
Falls back to existing TTS service if ElevenLabs is unavailable.
"""

import asyncio
import hashlib
import io
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import httpx

from config import settings

logger = logging.getLogger("live_takeover.voice_clone")

# Storage for synthesized audio
CLONE_AUDIO_DIR = Path(
    getattr(settings, 'AUDIO_STORAGE_PATH', './storage/audio')
) / 'cloned'
CLONE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


class VoiceCloneService:
    """
    ElevenLabs voice cloning integration.
    Supports: voice creation from samples, TTS with cloned voice, voice management.
    Falls back to existing TTS if ElevenLabs API key not set.
    """
    
    ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
    
    def __init__(self):
        self.api_key = getattr(settings, 'ELEVENLABS_API_KEY', '')
        self.model_id = getattr(settings, 'ELEVENLABS_MODEL', 'eleven_turbo_v2_5')
        self._available = bool(self.api_key)
        self._voice_cache: Dict[str, Dict[str, Any]] = {}  # voice_id -> metadata
        self._audio_cache: Dict[str, bytes] = {}  # text_hash -> audio bytes
        
        if not self._available:
            logger.warning("ElevenLabs API key not set. Voice cloning disabled. "
                         "Set ELEVENLABS_API_KEY in config.")
        else:
            logger.info("ElevenLabs voice clone service initialized")
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def _headers(self) -> Dict[str, str]:
        return {
            "xi-api-key": self.api_key,
            "Accept": "application/json"
        }
    
    async def create_voice_clone(
        self,
        name: str,
        audio_samples: List[bytes],
        description: str = "HoneyBadger voice clone",
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a voice clone from audio samples using ElevenLabs Instant Voice Cloning.
        
        Args:
            name: Name for the cloned voice
            audio_samples: List of audio file bytes (WAV/MP3, min 1 sample, 1-2 min total)
            description: Voice description
            labels: Optional metadata labels
            
        Returns:
            {"voice_id": str, "name": str} or None on failure
        """
        if not self._available:
            logger.error("ElevenLabs not available for voice cloning")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Build multipart form
                files = []
                for i, sample in enumerate(audio_samples):
                    files.append(
                        ("files", (f"sample_{i}.wav", sample, "audio/wav"))
                    )
                
                data = {
                    "name": name,
                    "description": description,
                }
                if labels:
                    import json
                    data["labels"] = json.dumps(labels)
                
                response = await client.post(
                    f"{self.ELEVENLABS_BASE_URL}/voices/add",
                    headers={"xi-api-key": self.api_key},
                    data=data,
                    files=files
                )
                
                if response.status_code == 200:
                    result = response.json()
                    voice_id = result.get("voice_id")
                    logger.info(f"Voice clone created: {voice_id} ({name})")
                    
                    voice_meta = {
                        "voice_id": voice_id,
                        "name": name,
                        "description": description
                    }
                    self._voice_cache[voice_id] = voice_meta
                    return voice_meta
                else:
                    logger.error(f"Voice clone creation failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Voice clone creation error: {e}", exc_info=True)
            return None
    
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        session_id: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """
        Synthesize speech using a cloned voice.
        
        Args:
            text: Text to speak
            voice_id: ElevenLabs voice ID
            session_id: Optional session ID for file organization
            stability: Voice stability (0-1, lower = more expressive)
            similarity_boost: Voice clarity (0-1, higher = closer to clone)
            style: Style exaggeration (0-1)
            
        Returns:
            {"audio_data": bytes, "audio_path": str, "duration": float} or None
        """
        if not self._available:
            return await self._fallback_synthesize(text, session_id)
        
        # Check cache first
        cache_key = hashlib.md5(f"{text}:{voice_id}".encode()).hexdigest()
        if cache_key in self._audio_cache:
            logger.debug("TTS cache hit")
            audio_data = self._audio_cache[cache_key]
            audio_path = self._save_audio(audio_data, cache_key, session_id)
            return {
                "audio_data": audio_data,
                "audio_path": audio_path,
                "duration": self._estimate_duration(audio_data),
                "cached": True
            }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "text": text,
                    "model_id": self.model_id,
                    "voice_settings": {
                        "stability": stability,
                        "similarity_boost": similarity_boost,
                        "style": style,
                        "use_speaker_boost": True
                    }
                }
                
                response = await client.post(
                    f"{self.ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": self.api_key,
                        "Content-Type": "application/json",
                        "Accept": "audio/mpeg"
                    },
                    json=payload
                )
                
                if response.status_code == 200:
                    audio_data = response.content
                    
                    # Cache the result
                    self._audio_cache[cache_key] = audio_data
                    
                    # Save to disk
                    audio_path = self._save_audio(audio_data, cache_key, session_id)
                    
                    duration = self._estimate_duration(audio_data)
                    
                    logger.info(f"TTS synthesized: {len(text)} chars → {len(audio_data)} bytes")
                    
                    return {
                        "audio_data": audio_data,
                        "audio_path": audio_path,
                        "duration": duration,
                        "cached": False
                    }
                else:
                    logger.error(f"TTS synthesis failed: {response.status_code} - {response.text}")
                    return await self._fallback_synthesize(text, session_id)
                    
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}", exc_info=True)
            return await self._fallback_synthesize(text, session_id)
    
    async def list_voices(self) -> List[Dict[str, Any]]:
        """List all available voices (including clones)."""
        if not self._available:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.ELEVENLABS_BASE_URL}/voices",
                    headers=self._headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    voices = data.get("voices", [])
                    return [
                        {
                            "voice_id": v["voice_id"],
                            "name": v["name"],
                            "category": v.get("category", "unknown"),
                            "labels": v.get("labels", {}),
                            "preview_url": v.get("preview_url")
                        }
                        for v in voices
                    ]
                return []
        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            return []
    
    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a cloned voice."""
        if not self._available:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.delete(
                    f"{self.ELEVENLABS_BASE_URL}/voices/{voice_id}",
                    headers=self._headers()
                )
                
                if response.status_code == 200:
                    self._voice_cache.pop(voice_id, None)
                    logger.info(f"Voice deleted: {voice_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete voice: {e}")
            return False
    
    async def get_quota(self) -> Optional[Dict[str, Any]]:
        """Check ElevenLabs usage quota."""
        if not self._available:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.ELEVENLABS_BASE_URL}/user/subscription",
                    headers=self._headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "character_count": data.get("character_count", 0),
                        "character_limit": data.get("character_limit", 0),
                        "remaining": data.get("character_limit", 0) - data.get("character_count", 0),
                        "tier": data.get("tier", "free")
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get quota: {e}")
            return None
    
    async def preview_voice(
        self,
        text: str,
        voice_id: str
    ) -> Optional[bytes]:
        """Generate a quick audio preview with a voice."""
        result = await self.synthesize(text, voice_id)
        if result:
            return result["audio_data"]
        return None
    
    def _save_audio(
        self, 
        audio_data: bytes, 
        filename_base: str, 
        session_id: Optional[str] = None
    ) -> str:
        """Upload audio bytes to Cloudinary and return secure URL."""
        try:
            from services.cloudinary_service import cloudinary_service, FOLDER_AUDIO_SYNTHESIZED
            filename = f"clone_{filename_base}.mp3"
            folder = f"{FOLDER_AUDIO_SYNTHESIZED}/{session_id}" if session_id else FOLDER_AUDIO_SYNTHESIZED
            return cloudinary_service.upload_audio(audio_data, filename, folder=folder)
        except Exception as e:
            logger.error(f"Cloudinary upload failed, falling back to local: {e}")
            # Fallback: save locally so the call doesn't break
            if session_id:
                output_dir = CLONE_AUDIO_DIR / session_id
                output_dir.mkdir(parents=True, exist_ok=True)
            else:
                output_dir = CLONE_AUDIO_DIR
            filepath = output_dir / f"clone_{filename_base}.mp3"
            filepath.write_bytes(audio_data)
            return str(filepath)
    
    def _estimate_duration(self, audio_data: bytes) -> float:
        """Estimate audio duration from MP3 data."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
            return len(audio) / 1000.0  # ms to seconds
        except Exception:
            # Rough estimate: MP3 at 128kbps
            return len(audio_data) / (128 * 1024 / 8)
    
    async def _fallback_synthesize(
        self, 
        text: str, 
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fallback to existing TTS service when ElevenLabs unavailable."""
        try:
            from services.tts_service import tts_service
            
            result = tts_service.synthesize(
                text=text,
                language="en",
                session_id=session_id or "live-fallback"
            )
            
            if result.get("audio_path"):
                audio_path = result["audio_path"]
                audio_data = b""
                if os.path.exists(audio_path):
                    with open(audio_path, "rb") as f:
                        audio_data = f.read()
                
                return {
                    "audio_data": audio_data,
                    "audio_path": audio_path,
                    "duration": result.get("duration", 0.0),
                    "cached": False,
                    "fallback": True
                }
            return None
        except Exception as e:
            logger.error(f"Fallback TTS failed: {e}")
            return None
    
    def clear_cache(self):
        """Clear the audio cache."""
        self._audio_cache.clear()
        logger.info("Voice clone audio cache cleared")


# Module-level singleton
voice_clone_service = VoiceCloneService()
