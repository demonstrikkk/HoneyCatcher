"""
Text-to-Speech Service using Piper TTS
Generates natural-sounding voice from text
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict
import hashlib

try:
    import pyttsx3  # Fallback TTS
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    from gtts import gTTS  # High-quality online fallback
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

from config import settings
from services.elevenlabs_service import elevenlabs_service

logger = logging.getLogger("tts_service")

class TTSService:
    """
    Production-grade Text-to-Speech service
    """
    
    def __init__(self):
        self.engine_type = getattr(settings, 'TTS_ENGINE', 'system')  # 'piper' or 'system'
        self.voice_path = Path(getattr(settings, 'TTS_VOICE_PATH', './models/voices'))
        self.output_path = Path(getattr(settings, 'AUDIO_STORAGE_PATH', './storage/audio')) / 'synthesized'
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Voice mapping for different languages
        self.voice_map = {
            'en': 'en_US-lessac-medium',  # English (US)
            'hi': 'hi_IN-medium',          # Hindi
            'ta': 'ta_IN-medium',          # Tamil
            'te': 'te_IN-medium',          # Telugu
            'ml': 'ml_IN-medium',          # Malayalam
            'bn': 'bn_IN-medium',          # Bengali
        }
        
        self._pyttsx3_engine = None
        self._initialized = False
    
    def initialize(self):
        """
        Initialize TTS engine (lazy loading)
        """
        if self._initialized:
            return
            
        if self.engine_type == 'system' and PYTTSX3_AVAILABLE:
            try:
                self._pyttsx3_engine = pyttsx3.init()
                # Configure voice properties
                self._pyttsx3_engine.setProperty('rate', 150)  # Speed
                self._pyttsx3_engine.setProperty('volume', 0.9)  # Volume
                self._initialized = True
                logger.info("✅ System TTS (pyttsx3) initialized")
            except Exception as e:
                logger.error(f"Failed to initialize pyttsx3: {e}")
        
        self._initialized = True
    
    async def synthesize(
        self,
        text: str,
        language: str = "en",
        session_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Synthesize speech from text
        
        Args:
            text: Text to synthesize
            language: Language code
            session_id: Optional session ID for file organization
            
        Returns:
            {
                "audio_path": str,
                "duration": float,
                "format": str,
                "language": str
            }
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # Generate unique filename
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            filename = f"tts_{language}_{text_hash}.wav"
            
            if session_id:
                output_dir = self.output_path / session_id
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / filename
            else:
                output_file = self.output_path / filename
            
            # Try ElevenLabs first (Primary high-quality TTS)
            try:
                from services.elevenlabs_service import elevenlabs_service
                el_result = await elevenlabs_service.synthesize(
                    text=text,
                    session_id=session_id
                )
                if el_result.get("audio_path") and not el_result.get("error"):
                    logger.info("✅ ElevenLabs TTS used as primary engine")
                    return {
                        "audio_path": el_result["audio_path"],
                        "duration": el_result.get("duration", 0.0),
                        "format": "mp3",
                        "language": language
                    }
            except Exception as el_err:
                logger.warning(f"ElevenLabs TTS failed in tts_service: {el_err}")
                
            # Try Piper next (Local fallback)
            if self.engine_type == 'piper':
                success = self._synthesize_piper(text, str(output_file), language)
                if success:
                    return self._build_result(str(output_file), language)
            
            # Fallback to gTTS (Higher quality online fallback)
            if GTTS_AVAILABLE:
                success = self._synthesize_gtts(text, str(output_file), language)
                if success:
                    return self._build_result(str(output_file), language)

            # Fallback to system TTS
            if self._pyttsx3_engine:
                self._synthesize_system(text, str(output_file))
                return self._build_result(str(output_file), language)
            
            # If all fails, return error
            logger.error("No TTS engine available")
            return self._fallback_synthesis()
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}", exc_info=True)
            return self._fallback_synthesis()
    
    def _synthesize_piper(self, text: str, output_file: str, language: str) -> bool:
        """
        Synthesize using Piper TTS (subprocess call)
        """
        try:
            voice_model = self.voice_map.get(language, self.voice_map['en'])
            voice_file = self.voice_path / f"{voice_model}.onnx"
            
            if not voice_file.exists():
                logger.warning(f"Piper voice model not found: {voice_file}")
                return False
            
            # Call piper CLI
            cmd = [
                "piper",
                "--model", str(voice_file),
                "--output_file", output_file
            ]
            
            result = subprocess.run(
                cmd,
                input=text.encode('utf-8'),
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                logger.info(f"Piper synthesis successful: {output_file}")
                return True
            else:
                logger.error(f"Piper synthesis failed: {result.stderr.decode()}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Piper synthesis timeout")
            return False
        except FileNotFoundError:
            logger.warning("Piper CLI not found. Install: pip install piper-tts")
            return False
        except Exception as e:
            logger.error(f"Piper synthesis error: {e}")
            return False
    
    def _synthesize_gtts(self, text: str, output_file: str, language: str) -> bool:
        """
        Synthesize using gTTS (Google TTS)
        """
        try:
            # gTTS supports ISO codes (hi, ta, te, ml)
            tts = gTTS(text=text, lang=language)
            tts.save(output_file)
            logger.info(f"gTTS synthesis successful: {output_file}")
            return True
        except Exception as e:
            logger.error(f"gTTS synthesis failed: {e}")
            return False

    def _synthesize_system(self, text: str, output_file: str):
        """
        Synthesize using system TTS (pyttsx3)
        """
        try:
            self._pyttsx3_engine.save_to_file(text, output_file)
            self._pyttsx3_engine.runAndWait()
            logger.info(f"System TTS synthesis successful: {output_file}")
        except Exception as e:
            logger.error(f"System TTS synthesis failed: {e}")
            raise
    
    def _build_result(self, audio_path: str, language: str) -> Dict[str, any]:
        """
        Build synthesis result dictionary.
        Uploads the audio to Cloudinary and returns the secure URL.
        """
        # Get audio duration (approximate)
        duration = self._estimate_duration(audio_path)
        
        # Upload to Cloudinary for persistent storage
        audio_url = audio_path  # fallback to local path if upload fails
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
            "format": "wav",
            "language": language
        }
    
    def _estimate_duration(self, audio_path: str) -> float:
        """
        Estimate audio duration
        """
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_wav(audio_path)
            return audio.duration_seconds
        except Exception:
            # Rough estimate: ~150 words per minute, ~5 chars per word
            # Just return 0 if we can't measure
            return 0.0
    
    def _fallback_synthesis(self) -> Dict[str, any]:
        """
        Fallback when TTS unavailable
        """
        return {
            "audio_path": None,
            "duration": 0.0,
            "format": "wav",
            "language": "en",
            "error": "TTS service unavailable"
        }
    
    async def synthesize_to_bytes(
        self,
        text: str,
        voice_id: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Synthesize speech and return raw audio bytes (mp3) in memory.
        Used for transient live WebRTC injection — no file save, no Cloudinary.

        Args:
            text: Text to synthesize
            voice_id: ElevenLabs voice ID (defaults to Rachel)

        Returns:
            Raw mp3 bytes, or None on failure
        """
        import httpx

        api_key = getattr(settings, 'ELEVENLABS_API_KEY', '')
        if not api_key:
            logger.error("ElevenLabs API key not configured for synthesize_to_bytes")
            return None

        if not voice_id:
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel (default free voice)

        model = getattr(settings, 'ELEVENLABS_MODEL', 'eleven_turbo_v2_5')

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    json={
                        "text": text,
                        "model_id": model,
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                            "style": 0.0,
                            "use_speaker_boost": True
                        }
                    },
                    headers={
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                        "xi-api-key": api_key
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    logger.info(f"✅ synthesize_to_bytes: {len(response.content)} bytes")
                    return response.content
                else:
                    logger.error(f"ElevenLabs API error ({response.status_code}): {response.text}")
                    return None
        except Exception as e:
            logger.error(f"synthesize_to_bytes failed: {e}", exc_info=True)
            return None

    def get_supported_languages(self) -> list:
        """
        Get list of supported languages
        """
        return list(self.voice_map.keys())


# Singleton instance
tts_service = TTSService()
