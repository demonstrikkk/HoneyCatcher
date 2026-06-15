import io
import os
import tempfile
import logging
from pathlib import Path
from groq import AsyncGroq
from config import settings

logger = logging.getLogger(__name__)
_groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)


async def transcribe_bytes(audio_bytes: bytes, fmt: str = "wav") -> dict:
    with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            result = await _groq_client.audio.transcriptions.create(
                file=(Path(tmp_path).name, f),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                language=None,
            )
        return {
            "text": result.text.strip(),
            "language": getattr(result, "language", "en"),
            "confidence": 0.95,
        }
    except Exception as e:
        logger.error("Groq Whisper error: %s", e)
        return {"text": "", "language": "en", "confidence": 0.0}
    finally:
        os.unlink(tmp_path)


async def transcribe_file(path: str) -> dict:
    audio_bytes = Path(path).read_bytes()
    fmt = Path(path).suffix.lstrip(".")
    return await transcribe_bytes(audio_bytes, fmt)
