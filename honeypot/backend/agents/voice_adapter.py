"""
Voice Adapter for HoneyPot Agent
Integrates voice processing into the agentic flow.
Handles the transformation of:
1. Scammer Audio -> Transcription -> Agent Input
2. Agent Reply -> Speech Naturalization -> TTS synthesis
"""

import logging
from typing import List, Dict, Optional
from agents.graph import agent_system
from agents.speech_naturalizer import speech_naturalizer
from services.stt_service import stt_service
from services.tts_service import tts_service
from services.audio_processor import audio_processor

logger = logging.getLogger("voice_adapter")

class VoiceAdapter:
    """
    Adapter to bridge voice I/O with the existing LangGraph agent.
    """
    
    def __init__(self):
        self.agent = agent_system
        self.stt = stt_service
        self.tts = tts_service
        self.naturalizer = speech_naturalizer
        self.processor = audio_processor

    async def process_scammer_audio(
        self, 
        session_id: str, 
        audio_data: bytes, 
        format: str = "wav",
        language: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Processes incoming scammer audio:
        1. Normalizes audio
        2. Transcribes to text
        3. Returns transcription results
        """
        try:
            # 1. Normalize
            normalized_audio, metadata = self.processor.normalize_audio(audio_data, source_format=format)
            
            # 2. Transcribe
            stt_result = self.stt.transcribe_bytes(
                normalized_audio, 
                format="wav", 
                language=language
            )
            
            return {
                "text": stt_result["text"],
                "language": stt_result["language"],
                "confidence": stt_result["confidence"],
                "duration": stt_result["duration"],
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"Failed to process scammer audio: {e}", exc_info=True)
            return {
                "text": "",
                "language": language or "en",
                "confidence": 0.0,
                "error": str(e)
            }

    async def generate_agent_voice(
        self, 
        session_id: str, 
        text_response: str, 
        language: str = "en",
        mode: str = "ai_speaks"
    ) -> Dict[str, any]:
        """
        Processes outgoing agent response:
        1. Naturalizes text for speech
        2. Synthesizes audio if mode is ai_speaks
        3. Returns result
        """
        try:
            # 1. Naturalize
            naturalized_text = await self.naturalizer.naturalize(text_response, language=language)
            
            result = {
                "naturalized_text": naturalized_text,
                "original_text": text_response,
                "mode": mode
            }
            
            # 2. Synthesize if autonomous mode
            if mode == "ai_speaks":
                tts_result = self.tts.synthesize(
                    naturalized_text, 
                    language=language, 
                    session_id=session_id
                )
                result["audio_path"] = tts_result["audio_path"]
                result["duration"] = tts_result["duration"]
            
            return result
        except Exception as e:
            logger.error(f"Failed to generate agent voice: {e}", exc_info=True)
            return {
                "naturalized_text": text_response,
                "original_text": text_response,
                "error": str(e)
            }

    async def run_voice_turn(
        self, 
        session_id: str, 
        audio_data: bytes, 
        history: List[Dict[str, str]],
        mode: str = "ai_speaks",
        format: str = "wav"
    ) -> Dict[str, any]:
        """
        Complete loop for a single voice turn.
        """
        # 1. Scammer speaks -> Text
        scammer_input = await self.process_scammer_audio(session_id, audio_data, format=format)
        
        if not scammer_input["text"]:
            return {"error": "No speech detected"}

        # 2. Update history
        full_history = history + [{"role": "scammer", "content": scammer_input["text"]}]
        
        # 3. Existing Agent Decision
        agent_reply_text = await self.agent.run(full_history)
        
        # 4. Agent Text -> Voice
        voice_output = await self.generate_agent_voice(
            session_id, 
            agent_reply_text, 
            language=scammer_input["language"],
            mode=mode
        )
        
        return {
            "scammer_transcription": scammer_input["text"],
            "scammer_language": scammer_input["language"],
            "agent_reply": agent_reply_text,
            "agent_naturalized": voice_output["naturalized_text"],
            "agent_audio_path": voice_output.get("audio_path"),
            "mode": mode
        }

# Singleton instance
voice_adapter = VoiceAdapter()
