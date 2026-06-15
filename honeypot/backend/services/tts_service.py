import io
import logging
from pathlib import Path
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from config import settings

logger = logging.getLogger(__name__)

_el = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)


def _synth(text: str, voice_id: str) -> bytes:
    audio_gen = _el.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.8,
            style=0.0,
            use_speaker_boost=True,
        ),
        output_format="mp3_44100_128",
    )
    return b"".join(audio_gen)


async def synthesize_to_bytes(text: str, voice_id: str | None = None) -> bytes:
    import asyncio

    vid = voice_id or settings.ELEVENLABS_VOICE_ID
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _synth, text, vid)


class TTSService:
    async def synthesize(self, text: str, language: str = "en", session_id: str | None = None) -> dict:
        audio_bytes = await synthesize_to_bytes(text)
        path = None
        if session_id:
            path_obj = Path("storage/audio") / session_id / f"tts_{hash(text)}.mp3"
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            path_obj.write_bytes(audio_bytes)
            path = str(path_obj)
        return {
            "audio_path": path,
            "duration": 0.0,
            "format": "mp3",
            "voice_id": None,
            "voice_name": None,
        }


tts_service = TTSService()
