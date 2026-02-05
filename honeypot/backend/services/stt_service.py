"""
Speech-to-Text Service using Faster-Whisper
Handles audio transcription with language detection
"""

import os
import logging
from typing import Tuple, Optional, Dict
from pathlib import Path

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logging.warning("faster-whisper not installed. Install with: pip install faster-whisper")

from config import settings

logger = logging.getLogger("stt_service")

class STTService:
    """
    Production-grade Speech-to-Text service using Whisper
    """
    
    def __init__(self):
        self.model_size = getattr(settings, 'WHISPER_MODEL', 'tiny')  # Switched to tiny for speed
        self.device = "cpu"  # Use "cuda" if GPU available
        self.compute_type = "int8"  # int8 for CPU, float16 for GPU
        
        self.model: Optional[WhisperModel] = None
        self._initialized = False
        
        # Language mapping for common scam languages
        self.language_map = {
            'en': 'English',
            'hi': 'Hindi',
            'ta': 'Tamil',
            'te': 'Telugu',
            'bn': 'Bengali',
            'mr': 'Marathi',
            'gu': 'Gujarati',
            'kn': 'Kannada',
            'ml': 'Malayalam',
            'pa': 'Punjabi'
        }
    
    def initialize(self):
        """
        Initialize Whisper model (lazy loading)
        """
        if self._initialized:
            return
            
        if not WHISPER_AVAILABLE:
            logger.error("Whisper not available. Cannot initialize STT service.")
            return
            
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            self._initialized = True
            logger.info("✅ Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Whisper model: {e}", exc_info=True)
            self.model = None
    
    def transcribe(
        self, 
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Transcribe audio file to text
        
        Args:
            audio_path: Path to audio file
            language: Optional language code (auto-detect if None)
            
        Returns:
            {
                "text": str,
                "language": str,
                "language_name": str,
                "confidence": float,
                "duration": float
            }
        """
        # Initialize on first use
        if not self._initialized:
            self.initialize()
        
        if not self.model:
            logger.error("Whisper model not available")
            return self._fallback_transcription()
        
        try:
            # Transcribe with Whisper
            segments, info = self.model.transcribe(
                audio_path,
                language=language,  # Auto-detect if None
                beam_size=5,
                vad_filter=True,  # Voice Activity Detection (removes silence)
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Combine all segments
            full_text = " ".join([segment.text.strip() for segment in segments])
            
            # Language info
            detected_lang = info.language if hasattr(info, 'language') else 'en'
            lang_name = self.language_map.get(detected_lang, detected_lang)
            
            # Confidence (average of all segments)
            confidences = [segment.avg_logprob for segment in segments]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            # Convert log probability to 0-1 scale (approximate)
            confidence_score = min(max((avg_confidence + 1.0) / 1.0, 0.0), 1.0)
            
            result = {
                "text": full_text,
                "language": detected_lang,
                "language_name": lang_name,
                "confidence": round(confidence_score, 3),
                "duration": info.duration if hasattr(info, 'duration') else 0.0
            }
            
            logger.info(f"Transcription complete: {result['language_name']}, confidence: {result['confidence']}")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            return self._fallback_transcription()
    
    def transcribe_bytes(
        self,
        audio_data: bytes,
        format: str = "wav",
        language: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Transcribe audio from bytes (creates temp file)
        """
        import tempfile
        
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            
            # Transcribe
            result = self.transcribe(tmp_path, language)
            
            # Cleanup
            os.remove(tmp_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription from bytes failed: {e}")
            return self._fallback_transcription()
    
    def detect_language(self, audio_path: str) -> str:
        """
        Detect language only (faster than full transcription)
        """
        if not self._initialized:
            self.initialize()
            
        if not self.model:
            return "en"
        
        try:
            _, info = self.model.transcribe(audio_path, max_initial_timestamp=5.0)
            return info.language if hasattr(info, 'language') else 'en'
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "en"
    
    def _fallback_transcription(self) -> Dict[str, any]:
        """
        Fallback when Whisper unavailable
        """
        return {
            "text": "[Transcription unavailable - Whisper not initialized]",
            "language": "en",
            "language_name": "English",
            "confidence": 0.0,
            "duration": 0.0
        }
    
    def get_supported_languages(self) -> dict:
        """
        Get list of supported languages
        """
        return self.language_map


# Singleton instance
stt_service = STTService()
