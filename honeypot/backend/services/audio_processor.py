"""
Audio Processing Utilities
Handles audio chunking, validation, format conversion, and storage
"""

import os
import base64
import hashlib
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
import logging

try:
    from pydub import AudioSegment
    import numpy as np
    import soundfile as sf
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    AUDIO_LIBS_AVAILABLE = False
    logging.warning("Audio libraries not installed. Install with: pip install pydub numpy soundfile")

from config import settings

logger = logging.getLogger("audio_processor")

class AudioProcessor:
    """
    Production-grade audio processing service
    """
    
    def __init__(self):
        self.storage_path = Path(getattr(settings, 'AUDIO_STORAGE_PATH', './storage/audio'))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Audio constraints
        self.target_sample_rate = 16000  # Whisper requirement
        self.target_channels = 1  # Mono
        self.chunk_duration = 2.0  # seconds
        self.max_chunk_size = 10 * 1024 * 1024  # 10MB
        
    def validate_audio(self, audio_data: bytes, format: str = "wav") -> bool:
        """
        Validate audio data integrity and format
        """
        if not AUDIO_LIBS_AVAILABLE:
            logger.error("Audio libraries not available")
            return False
            
        if len(audio_data) == 0:
            logger.error("Empty audio data")
            return False
            
        if len(audio_data) > self.max_chunk_size:
            logger.error(f"Audio chunk exceeds max size: {len(audio_data)} bytes")
            return False
            
        try:
            # Try to load audio
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format=format)
            
            # Basic sanity checks
            if audio.duration_seconds < 0.1 or audio.duration_seconds > 30:
                logger.warning(f"Unusual audio duration: {audio.duration_seconds}s")
                
            return True
        except Exception as e:
            logger.error(f"Audio validation failed: {e}")
            return False
    
    def normalize_audio(self, audio_data: bytes, source_format: str = "webm") -> Tuple[bytes, dict]:
        """
        Convert audio to standardized format (16kHz, mono, WAV)
        Returns: (normalized_audio_bytes, metadata)
        """
        if not AUDIO_LIBS_AVAILABLE:
            raise Exception("Audio libraries not installed")
            
        try:
            # Load audio
            audio = AudioSegment.from_file(
                io.BytesIO(audio_data), 
                format=source_format
            )
            
            # Convert to mono
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Resample to 16kHz
            if audio.frame_rate != self.target_sample_rate:
                audio = audio.set_frame_rate(self.target_sample_rate)
            
            # Export as WAV (lossless, Whisper-friendly)
            buffer = io.BytesIO()
            audio.export(buffer, format="wav")
            normalized_data = buffer.getvalue()
            
            metadata = {
                "sample_rate": self.target_sample_rate,
                "channels": 1,
                "duration": audio.duration_seconds,
                "original_format": source_format,
                "normalized_format": "wav"
            }
            
            logger.info(f"Normalized audio: {metadata}")
            return normalized_data, metadata
            
        except Exception as e:
            logger.error(f"Audio normalization failed: {e}", exc_info=True)
            raise
    
    def save_chunk(
        self, 
        session_id: str, 
        audio_data: bytes, 
        sequence_number: int,
        format: str = "wav"
    ) -> str:
        """
        Save audio chunk to disk
        Returns: file_path
        """
        try:
            # Create session folder
            session_folder = self.storage_path / session_id
            session_folder.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp and sequence
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"chunk_{sequence_number:04d}_{timestamp}.{format}"
            file_path = session_folder / filename
            
            # Write file
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            logger.info(f"Saved audio chunk: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save audio chunk: {e}", exc_info=True)
            raise
    
    def load_chunk(self, file_path: str) -> bytes:
        """
        Load audio chunk from disk
        """
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load audio chunk: {e}")
            raise
    
    def decode_base64_audio(self, base64_data: str) -> bytes:
        """
        Decode base64-encoded audio data
        """
        try:
            # Handle data URLs (e.g., "data:audio/wav;base64,...")
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            return base64.b64decode(base64_data)
        except Exception as e:
            logger.error(f"Failed to decode base64 audio: {e}")
            raise
    
    def get_audio_duration(self, audio_data: bytes, format: str = "wav") -> float:
        """
        Get audio duration in seconds
        """
        if not AUDIO_LIBS_AVAILABLE:
            return 0.0
            
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format=format)
            return audio.duration_seconds
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0.0
    
    def cleanup_session_audio(self, session_id: str):
        """
        Delete all audio files for a session
        """
        try:
            session_folder = self.storage_path / session_id
            if session_folder.exists():
                import shutil
                shutil.rmtree(session_folder)
                logger.info(f"Cleaned up audio for session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup session audio: {e}")


# Add missing import
import io

# Singleton instance
audio_processor = AudioProcessor()
