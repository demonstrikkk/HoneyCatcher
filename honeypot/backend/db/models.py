from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class BaseDoc(BaseModel):
    model_config = ConfigDict(extra="ignore")

class AgentState(BaseDoc):
    """Internal state of the agent for LangGraph."""
    turn_count: int = 0
    sentiment: str = "neutral"
    last_action: str = "listen"
    notes: str = ""

class Message(BaseDoc):
    """
    Represents a single message in the conversation.
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    sender: str  # "scammer" or "agent"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Voice fields (NEW)
    is_voice: bool = False
    audio_file_path: Optional[str] = None
    transcription_confidence: Optional[float] = None
    speech_naturalized: bool = False  # For agent responses

class Intelligence(BaseDoc):
    """
    Structured intelligence extracted from the conversation.
    """
    bank_accounts: List[str] = Field(default_factory=list)
    upi_ids: List[str] = Field(default_factory=list)
    phone_numbers: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    scam_keywords: List[str] = Field(default_factory=list)
    behavioral_tactics: List[str] = Field(default_factory=list)

class Session(BaseDoc):
    """
    Represents a full scam engagement session.
    """
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"  # active, terminated, reported
    message_count: int = 0
    scam_score: float = 0.0
    is_confirmed_scam: bool = False
    
    # Intelligence
    extracted_intelligence: Intelligence = Field(default_factory=Intelligence)
    
    # Agent Memory
    agent_state: AgentState = Field(default_factory=AgentState)
    
    # Metadata
    client_ip: Optional[str] = None
    language: str = "en"
    
    # Voice fields (NEW)
    voice_enabled: bool = False
    detected_language: Optional[str] = None  # From Whisper
    voice_mode: str = "text"  # "text" | "ai_speaks" | "ai_suggests"
    audio_chunk_count: int = 0
    total_audio_duration: float = 0.0  # seconds

class VoiceChunk(BaseDoc):
    """
    Represents an audio chunk for processing.
    """
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    file_path: str  # Path to stored audio file
    format: str = "wav"  # wav, mp3, webm
    sample_rate: int = 16000
    duration: float  # seconds
    sequence_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = False
    transcription: Optional[str] = None
    transcription_confidence: Optional[float] = None
