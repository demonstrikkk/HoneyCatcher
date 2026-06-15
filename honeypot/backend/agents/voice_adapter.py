import logging
from typing import List, Dict, Optional
from agents.graph import run_agent
from agents.speech_naturalizer import speech_naturalizer
from services.stt_service import transcribe_bytes
from services.tts_service import synthesize_to_bytes
from services.audio_processor import audio_processor

logger = logging.getLogger("voice_adapter")


class VoiceAdapter:

    def __init__(self):
        self.naturalizer = speech_naturalizer
        self.processor = audio_processor

    async def process_scammer_audio(
        self,
        session_id: str,
        audio_data: bytes,
        format: str = "wav",
        language: Optional[str] = None
    ) -> Dict[str, any]:
        try:
            normalized_audio, metadata = self.processor.normalize_audio(audio_data, source_format=format)

            stt_result = await transcribe_bytes(normalized_audio, fmt="wav")

            return {
                "text": stt_result.get("text", ""),
                "language": stt_result.get("language", "en"),
                "confidence": stt_result.get("confidence", 0.0),
                "duration": metadata.get("duration", 0),
                "metadata": metadata,
            }
        except Exception as e:
            logger.error("Failed to process scammer audio: %s", e, exc_info=True)
            return {
                "text": "",
                "language": language or "en",
                "confidence": 0.0,
                "error": str(e),
            }

    async def generate_agent_voice(
        self,
        session_id: str,
        text_response: str,
        language: str = "en",
        mode: str = "ai_speaks"
    ) -> Dict[str, any]:
        try:
            naturalized_text = await self.naturalizer.naturalize(text_response, language=language)

            result = {
                "naturalized_text": naturalized_text,
                "original_text": text_response,
                "mode": mode,
            }

            if mode == "ai_speaks":
                try:
                    from services.elevenlabs_service import elevenlabs_service
                    tts_result = await elevenlabs_service.synthesize(
                        text=naturalized_text,
                        session_id=session_id,
                    )
                    if tts_result.get("audio_path") and not tts_result.get("error"):
                        result["audio_path"] = tts_result["audio_path"]
                        result["duration"] = tts_result.get("duration", 0)
                        result["voice_name"] = tts_result.get("voice_name", "Rachel")
                    else:
                        raise Exception(tts_result.get("error", "ElevenLabs returned no audio"))
                except Exception as e:
                    logger.warning("ElevenLabs TTS failed, falling back: %s", e)
                    audio_bytes = await synthesize_to_bytes(naturalized_text)
                    result["audio_bytes"] = audio_bytes

            return result
        except Exception as e:
            logger.error("Failed to generate agent voice: %s", e, exc_info=True)
            return {
                "naturalized_text": text_response,
                "original_text": text_response,
                "error": str(e),
            }

    async def run_voice_turn(
        self,
        session_id: str,
        audio_data: bytes,
        history: List[Dict[str, str]],
        mode: str = "ai_speaks",
        format: str = "wav"
    ) -> Dict[str, any]:
        scammer_input = await self.process_scammer_audio(session_id, audio_data, format=format)

        if not scammer_input.get("text"):
            return {"error": "No speech detected"}

        full_history = history + [{"speaker": "scammer", "text": scammer_input["text"]}]

        agent_result = await run_agent(
            scammer_text=scammer_input["text"],
            history=full_history,
            mode="ai_takeover" if mode == "ai_speaks" else "ai_coached",
        )
        agent_reply_text = agent_result.get("ai_response") or agent_result.get("coaching_text", "")

        voice_output = await self.generate_agent_voice(
            session_id,
            agent_reply_text,
            language=scammer_input.get("language", "en"),
            mode=mode,
        )

        return {
            "scammer_transcription": scammer_input["text"],
            "scammer_language": scammer_input.get("language", "en"),
            "agent_reply": agent_reply_text,
            "agent_naturalized": voice_output.get("naturalized_text", agent_reply_text),
            "agent_audio_path": voice_output.get("audio_path"),
            "mode": mode,
            "agent_intent": agent_result.get("intent", "unknown"),
            "agent_strategy": agent_result.get("strategy", "unknown"),
        }


voice_adapter = VoiceAdapter()
