from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


def new_id() -> str:
    return str(uuid.uuid4())


# -- Users --------------------------------------------------------------------


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = ""


class UserInDB(BaseModel):
    user_id: str = Field(default_factory=new_id)
    username: str
    password_hash: str
    display_name: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None


class UserOut(BaseModel):
    user_id: str
    username: str
    display_name: str
    created_at: datetime


# -- Sessions -----------------------------------------------------------------


class SessionCreate(BaseModel):
    scammer_phone: Optional[str] = None
    operator_name: Optional[str] = None
    call_type: str = "ai_only"


class SessionInDB(BaseModel):
    session_id: str = Field(default_factory=new_id)
    user_id: Optional[str] = None
    scammer_phone: Optional[str] = None
    operator_name: Optional[str] = None
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    scam_score: float = 0.0
    is_confirmed_scam: bool = False
    extracted_intelligence: Dict[str, Any] = Field(default_factory=dict)
    agent_state: Dict[str, Any] = Field(default_factory=dict)
    voice_enabled: bool = False
    detected_language: str = "en"
    voice_mode: str = "text"
    metadata: Dict[str, Any] = Field(default_factory=dict)


# -- Messages -----------------------------------------------------------------


class MessageCreate(BaseModel):
    session_id: str
    content: str
    sender: str = "scammer"


class MessageInDB(BaseModel):
    message_id: str = Field(default_factory=new_id)
    session_id: str
    sender: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_voice: bool = False
    audio_file_path: Optional[str] = None
    transcription_confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


# -- Intelligence -------------------------------------------------------------


class EntityItem(BaseModel):
    type: str
    value: str
    confidence: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IntelligenceInDB(BaseModel):
    session_id: str
    entities: List[EntityItem] = Field(default_factory=list)
    tactics: List[str] = Field(default_factory=list)
    threat_level: int = 0
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


# -- Voice Clones -------------------------------------------------------------


class VoiceCloneInDB(BaseModel):
    clone_id: str = Field(default_factory=new_id)
    user_id: str
    voice_id: str
    voice_name: str
    audio_sample_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    settings: Dict[str, float] = Field(
        default_factory=lambda: {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.0,
        }
    )


# -- Legacy Models (for backward compat with existing features) ---------------


class BaseDoc(BaseModel):
    pass


class AgentState(BaseDoc):
    turn_count: int = 0
    sentiment: str = "neutral"
    last_action: str = "listen"
    notes: str = ""


class Message(BaseDoc):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    sender: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_voice: bool = False
    audio_file_path: Optional[str] = None
    transcription_confidence: Optional[float] = None
    speech_naturalized: bool = False


class Intelligence(BaseDoc):
    bank_accounts: List[str] = Field(default_factory=list)
    upi_ids: List[str] = Field(default_factory=list)
    phone_numbers: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    scam_keywords: List[str] = Field(default_factory=list)
    behavioral_tactics: List[str] = Field(default_factory=list)


class Session(BaseDoc):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"
    message_count: int = 0
    scam_score: float = 0.0
    is_confirmed_scam: bool = False
    extracted_intelligence: Intelligence = Field(default_factory=Intelligence)
    agent_state: AgentState = Field(default_factory=AgentState)
    client_ip: Optional[str] = None
    language: str = "en"
    voice_enabled: bool = False
    detected_language: Optional[str] = None
    voice_mode: str = "text"
    audio_chunk_count: int = 0
    total_audio_duration: float = 0.0
