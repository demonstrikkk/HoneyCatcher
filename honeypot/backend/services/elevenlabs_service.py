"""
ElevenLabs TTS Service - High-Quality AI Voice Generation
Provides free and premium voice synthesis with natural-sounding AI voices
"""

import os
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any
import httpx

from config import settings

logger = logging.getLogger("elevenlabs_service")


class ElevenLabsService:
    """
    ElevenLabs Text-to-Speech Service with Free Tier Support
    Provides access to all free ElevenLabs voices for natural AI speech
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'ELEVENLABS_API_KEY', '')
        self.model = getattr(settings, 'ELEVENLABS_MODEL', 'eleven_turbo_v2_5')
        self.base_url = "https://api.elevenlabs.io/v1"
        self.output_path = Path(getattr(settings, 'AUDIO_STORAGE_PATH', './storage/audio')) / 'synthesized'
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Cache for voices list
        self._voices_cache = None
        self._initialized = False
        
        # Free voices available in ElevenLabs (always accessible)
        self.free_voices = {
            "Rachel": "21m00Tcm4TlvDq8ikWAM",  # Female, American
            "Domi": "AZnzlk1XvdvUeBnXmlld",     # Female, American
            "Bella": "EXAVITQu4vr4xnSDxMaL",    # Female, American
            "Antoni": "ErXwobaYiN019PkySvjV",   # Male, American
            "Elli": "MF3mGyEYCl7XYWbV9V6O",     # Female, American
            "Josh": "TxGEqnHWrfWFTfGW9XjX",     # Male, American
            "Arnold": "VR6AewLTigWG4xSOukaG",   # Male, American
            "Adam": "pNInz6obpgDQGcFmaJgB",     # Male, American
            "Sam": "yoZ06aMxZJJ28mfd3POQ",      # Male, American
        }
        
    def initialize(self):
        """Initialize ElevenLabs service (lazy loading)"""
        if self._initialized:
            return
        
        if not self.api_key:
            logger.warning("⚠️ ElevenLabs API key not configured - using free tier defaults")
        else:
            logger.info("✅ ElevenLabs service initialized with API key")
        
        self._initialized = True
    
    async def get_available_voices(self) -> List[Dict]:
        """
        Get list of available voices from ElevenLabs
        Returns free voices even without API key
        
        Returns:
            List of voice objects with id, name, labels, category
        """
        if not self._initialized:
            self.initialize()
        
        # Return cached voices if available
        if self._voices_cache:
            return self._voices_cache
        
        try:
            if self.api_key:
                # Fetch from API if we have a key
                async with httpx.AsyncClient() as client:
                    headers = {"xi-api-key": self.api_key}
                    response = await client.get(
                        f"{self.base_url}/voices",
                        headers=headers,
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        voices = data.get('voices', [])
                        
                        # Format voices for easy consumption
                        self._voices_cache = [
                            {
                                "voice_id": voice['voice_id'],
                                "name": voice['name'],
                                "labels": voice.get('labels', {}),
                                "category": voice.get('category', 'general'),
                                "description": self._format_voice_description(voice)
                            }
                            for voice in voices
                        ]
                        
                        logger.info(f"✅ Fetched {len(self._voices_cache)} voices from ElevenLabs")
                        return self._voices_cache
                    else:
                        logger.warning(f"Failed to fetch voices: {response.status_code}")
            
            # Fallback to free voices (no API key required for listing)
            self._voices_cache = [
                {
                    "voice_id": voice_id,
                    "name": name,
                    "labels": {"accent": "american", "use_case": "general"},
                    "category": "premade",
                    "description": f"{name} - Natural {self._get_voice_gender(name)} voice"
                }
                for name, voice_id in self.free_voices.items()
            ]
            
            logger.info(f"✅ Using {len(self._voices_cache)} free ElevenLabs voices")
            return self._voices_cache
            
        except Exception as e:
            logger.error(f"Error fetching voices: {e}")
            # Return free voices as fallback
            return [
                {
                    "voice_id": voice_id,
                    "name": name,
                    "labels": {"accent": "american"},
                    "category": "premade",
                    "description": f"{name} - Free voice"
                }
                for name, voice_id in self.free_voices.items()
            ]
    
    def _format_voice_description(self, voice: Dict) -> str:
        """Format voice description from labels"""
        labels = voice.get('labels', {})
        gender = labels.get('gender', '')
        accent = labels.get('accent', '')
        age = labels.get('age', '')
        use_case = labels.get('use_case', '')
        
        parts = [voice['name']]
        if gender:
            parts.append(gender)
        if accent:
            parts.append(accent)
        if age:
            parts.append(age)
        if use_case:
            parts.append(f"({use_case})")
        
        return " - ".join(parts)
    
    def _get_voice_gender(self, name: str) -> str:
        """Get voice gender from name (heuristic for free voices)"""
        female_names = ["Rachel", "Domi", "Bella", "Elli"]
        return "female" if name in female_names else "male"
    
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        voice_name: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True
    ) -> Dict[str, Any]:
        """
        Synthesize speech from text using ElevenLabs
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use (if not provided, uses voice_name)
            voice_name: Voice name (e.g., "Rachel", "Antoni")
            session_id: Optional session ID for file organization
            model: Model to use (default: eleven_turbo_v2_5 for speed)
            stability: Voice stability (0-1)
            similarity_boost: Voice similarity (0-1)
            style: Style exaggeration (0-1)
            use_speaker_boost: Enable speaker boost for clarity
            
        Returns:
            {
                "audio_path": str,
                "duration": float,
                "format": str,
                "voice_id": str,
                "voice_name": str
            }
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # Determine voice_id
            if not voice_id:
                if voice_name:
                    voice_id = self.free_voices.get(voice_name)
                    if not voice_id:
                        # Try to find by name from available voices
                        voices = await self.get_available_voices()
                        matching = [v for v in voices if v['name'].lower() == voice_name.lower()]
                        if matching:
                            voice_id = matching[0]['voice_id']
                
                # Default to Rachel if nothing specified
                if not voice_id:
                    voice_id = self.free_voices["Rachel"]
                    voice_name = "Rachel"
            
            # Generate unique filename
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            filename = f"eleven_{voice_id[:8]}_{text_hash}.mp3"
            
            if session_id:
                output_dir = self.output_path / session_id
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / filename
            else:
                output_file = self.output_path / filename
            
            # Check if already synthesized (cache)
            if output_file.exists():
                logger.info(f"✅ Using cached audio: {output_file}")
                return self._build_result(str(output_file), voice_id, voice_name)
            
            # Synthesize with ElevenLabs API
            model = model or self.model
            
            async with httpx.AsyncClient() as client:
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json"
                }
                
                if self.api_key:
                    headers["xi-api-key"] = self.api_key
                
                payload = {
                    "text": text,
                    "model_id": model,
                    "voice_settings": {
                        "stability": stability,
                        "similarity_boost": similarity_boost,
                        "style": style,
                        "use_speaker_boost": use_speaker_boost
                    }
                }
                
                url = f"{self.base_url}/text-to-speech/{voice_id}"
                
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    # Save audio file
                    with open(output_file, 'wb') as f:
                        f.write(response.content)
                    
                    logger.info(f"✅ ElevenLabs synthesis successful: {output_file}")
                    
                    return self._build_result(str(output_file), voice_id, voice_name)
                else:
                    error_msg = response.text
                    logger.error(f"ElevenLabs API error ({response.status_code}): {error_msg}")
                    
                    # If API fails but we have fallback TTS, use it
                    return await self._fallback_to_system_tts(text, session_id)
                    
        except Exception as e:
            logger.error(f"ElevenLabs synthesis failed: {e}", exc_info=True)
            return await self._fallback_to_system_tts(text, session_id)
    
    async def _fallback_to_system_tts(self, text: str, session_id: Optional[str]) -> Dict:
        """Fallback to system TTS if ElevenLabs fails"""
        try:
            from services.tts_service import tts_service
            logger.warning("⚠️ Falling back to system TTS")
            return await tts_service.synthesize(text, session_id=session_id)
        except Exception as e:
            logger.error(f"Fallback TTS also failed: {e}")
            return {
                "audio_path": None,
                "duration": 0.0,
                "format": "mp3",
                "voice_id": None,
                "voice_name": None,
                "error": "TTS service unavailable"
            }
    
    def _build_result(self, audio_path: str, voice_id: str, voice_name: Optional[str]) -> Dict[str, Any]:
        """Build synthesis result dictionary — uploads to Cloudinary."""
        # Get audio duration
        duration = self._estimate_duration(audio_path)
        
        # Upload to Cloudinary for persistent storage
        audio_url = audio_path  # fallback
        try:
            from services.cloudinary_service import cloudinary_service, FOLDER_AUDIO_SYNTHESIZED
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            audio_url = cloudinary_service.upload_audio(
                audio_bytes,
                Path(audio_path).name,
                folder=FOLDER_AUDIO_SYNTHESIZED
            )
        except Exception as e:
            logger.error(f"Cloudinary upload failed, using local path: {e}")
        
        return {
            "audio_path": audio_url,
            "duration": duration,
            "format": "mp3",
            "voice_id": voice_id,
            "voice_name": voice_name or "Unknown"
        }
    
    def _estimate_duration(self, audio_path: str) -> float:
        """Estimate audio duration"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(audio_path)
            return audio.duration_seconds
        except Exception:
            return 0.0


# Singleton instance
elevenlabs_service = ElevenLabsService()
