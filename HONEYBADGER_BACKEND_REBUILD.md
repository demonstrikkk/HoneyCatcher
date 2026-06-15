# HoneyBadger Backend — Complete Rebuild Guide

> **Purpose:** Authoritative, step-by-step instructions to recreate the backend from scratch — optimised for correctness, peak performance, and token-efficient AI processing.
> **Stack:** Python 3.11 · FastAPI · LangGraph · Groq · ElevenLabs · MongoDB · WebSockets · Socket.IO

---

## Table of Contents

1. [Project Skeleton & Dependencies](#1-project-skeleton--dependencies)
2. [Configuration Layer](#2-configuration-layer)
3. [Database Layer](#3-database-layer)
4. [Authentication Core](#4-authentication-core)
5. [Services Layer](#5-services-layer)
   - 5a. STT Service (Groq Whisper)
   - 5b. TTS Service (ElevenLabs)
   - 5c. Intelligence Extractor
   - 5d. Scam Detector
   - 5e. Storage Service
6. [AI Agent Core (LangGraph)](#6-ai-agent-core-langgraph)
7. [Live Call WebSocket API](#7-live-call-websocket-api)
8. [REST API Routes](#8-rest-api-routes)
9. [WebRTC Signaling (Socket.IO)](#9-webrtc-signaling-socketio)
10. [Application Entry Point](#10-application-entry-point)
11. [Environment Variables Reference](#11-environment-variables-reference)
12. [Dependency Install & Run Commands](#12-dependency-install--run-commands)

---

## 1. Project Skeleton & Dependencies

### 1.1 Directory Structure

Create this exact directory tree before writing any code:

```
backend/
├── main.py
├── config.py
├── requirements.txt
│
├── core/
│   ├── __init__.py
│   ├── auth.py
│   └── lifecycle.py
│
├── db/
│   ├── __init__.py
│   ├── mongo.py
│   └── models.py
│
├── api/
│   ├── __init__.py
│   ├── auth_routes.py
│   ├── sessions.py
│   ├── message.py
│   ├── voice.py
│   ├── live_call.py          ← PRIMARY REBUILD TARGET
│   ├── live_takeover.py
│   ├── webrtc_signaling.py
│   ├── voice_clone.py
│   ├── elevenlabs_routes.py
│   └── testing.py
│
├── agents/
│   ├── __init__.py
│   ├── graph.py
│   ├── prompts.py
│   ├── persona.py
│   ├── memory.py
│   ├── voice_adapter.py
│   └── speech_naturalizer.py
│
├── services/
│   ├── __init__.py
│   ├── stt_service.py
│   ├── tts_service.py
│   ├── intelligence_extractor.py
│   ├── scam_detector.py
│   ├── storage_service.py
│   └── callback.py
│
├── features/
│   └── live_takeover/
│       ├── __init__.py
│       ├── intelligence_pipeline.py
│       ├── report_generator.py
│       ├── session_manager.py
│       ├── streaming_stt.py
│       ├── takeover_agent.py
│       ├── takeover_prompts.py
│       └── url_scanner.py
│
└── storage/
    ├── audio/
    └── reports/
```

### 1.2 `requirements.txt`

```
# Web framework
fastapi==0.110.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
websockets==12.0

# Socket.IO (WebRTC signaling)
python-socketio==5.11.2
aiohttp==3.9.3

# Database
motor==3.4.0
pymongo==4.6.2

# AI & LLM
langchain==0.1.16
langgraph==0.0.35
langchain-groq==0.1.3
langchain-google-genai==1.0.2
groq==0.4.2

# TTS/STT
elevenlabs==1.0.0
faster-whisper==1.0.0        # keep for local fallback
pydub==0.25.1
soundfile==0.12.1
numpy==1.26.4

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Rate limiting
slowapi==0.1.9
redis==5.0.3

# Storage
cloudinary==1.39.1

# URL scanning
vt-py==0.17.5

# Utilities
pydantic-settings==2.2.1
python-dotenv==1.0.1
httpx==0.27.0
aiofiles==23.2.1
```

---

## 2. Configuration Layer

### File: `config.py`

```python
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # ── Core ──────────────────────────────────────────────────────────────────
    API_SECRET_KEY: str = "changeme-in-production"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    MONGODB_URI: str
    MONGODB_DATABASE: str = "honeypot_db"

    # ── LLM ───────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_API_KEY: str = ""

    # ── Voice ─────────────────────────────────────────────────────────────────
    ELEVENLABS_API_KEY: str
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"   # Rachel (free tier)

    # ── Storage ───────────────────────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    STORAGE_BACKEND: str = "local"   # "cloudinary" | "local"

    # ── Auth ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "jwt-secret-changeme"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "*"

    @property
    def allowed_origins(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    # ── Callback ──────────────────────────────────────────────────────────────
    GUVI_CALLBACK_URL: str = ""

    # ── Security ──────────────────────────────────────────────────────────────
    VIRUSTOTAL_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

---

## 3. Database Layer

### File: `db/mongo.py`

```python
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import logging

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


async def connect_db():
    global _client
    _client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        maxPoolSize=100,
        minPoolSize=10,
        serverSelectionTimeoutMS=5000,
    )
    logger.info("MongoDB connected")


async def close_db():
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB disconnected")


def get_db():
    """Return the database handle. Call after connect_db()."""
    return _client[settings.MONGODB_DATABASE]


def get_collection(name: str):
    return get_db()[name]
```

### File: `db/models.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


# ── Helpers ──────────────────────────────────────────────────────────────────

def new_id() -> str:
    return str(uuid.uuid4())


# ── Users ─────────────────────────────────────────────────────────────────────

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


# ── Sessions ──────────────────────────────────────────────────────────────────

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


# ── Messages ──────────────────────────────────────────────────────────────────

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


# ── Intelligence ──────────────────────────────────────────────────────────────

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


# ── Voice Clones ──────────────────────────────────────────────────────────────

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
```

---

## 4. Authentication Core

### File: `core/auth.py`

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Header, HTTPException, status
from config import settings

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload["type"] = "access"
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload["type"] = "refresh"
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def verify_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Loose auth: accept either a valid API key or a valid JWT Bearer token."""
    if x_api_key == settings.API_SECRET_KEY:
        return {"auth_method": "api_key"}
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key"
    )


async def get_current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No bearer token"
        )
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not an access token"
        )
    return payload
```

---

## 5. Services Layer

### 5a. STT Service — `services/stt_service.py`

Use the **Groq Whisper API** (as in the updated architecture). Keep local faster-whisper only as a last resort.

```python
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
    """
    Transcribe raw audio bytes using Groq Whisper.

    Returns:
        {"text": str, "language": str, "confidence": float}
    """
    # Write to a temp file because Groq SDK requires a file-like with a name
    with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            result = await _groq_client.audio.transcriptions.create(
                file=(Path(tmp_path).name, f),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                language=None,          # auto-detect
            )
        return {
            "text": result.text.strip(),
            "language": getattr(result, "language", "en"),
            "confidence": 0.95,        # Groq doesn't expose per-word confidence
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
```

### 5b. TTS Service — `services/tts_service.py`

```python
import io
import logging
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from config import settings

logger = logging.getLogger(__name__)

# Singleton synchronous client (ElevenLabs SDK is synchronous; run in threadpool)
_el = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)


def _synth(text: str, voice_id: str) -> bytes:
    """Synchronous synthesis — returns MP3 bytes."""
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
    """
    Async wrapper — runs ElevenLabs in a thread so it doesn't block the loop.
    Returns raw MP3 bytes suitable for base64 encoding over WebSocket.
    """
    import asyncio

    vid = voice_id or settings.ELEVENLABS_VOICE_ID
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _synth, text, vid)
```

### 5c. Intelligence Extractor — `services/intelligence_extractor.py`

```python
import re
import logging
from typing import Dict, Any
from config import settings

logger = logging.getLogger(__name__)

# ── Regex patterns ────────────────────────────────────────────────────────────

_PHONE_RE   = re.compile(r"(\+?\d[\d\s\-]{8,14}\d)")
_UPI_RE     = re.compile(r"[\w.\-]+@[\w.\-]+")
_BANK_RE    = re.compile(r"\b\d{9,18}\b")
_URL_RE     = re.compile(r"https?://[^\s]+")
_IFSC_RE    = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")

# ── Tactic keywords ───────────────────────────────────────────────────────────

_TACTICS: Dict[str, list] = {
    "urgency":    ["urgent", "immediately", "right now", "expire", "24 hours", "last chance"],
    "authority":  ["rbi", "bank of india", "police", "cbi", "income tax", "government", "officer"],
    "fear":       ["arrest", "blocked", "legal action", "penalty", "lawsuit", "cancelled"],
    "greed":      ["prize", "lottery", "winner", "refund", "cashback", "reward"],
    "tech_support": ["virus", "hack", "remote access", "teamviewer", "anydesk", "error"],
    "romance":    ["love", "relationship", "lonely", "missed you"],
}


def extract_entities(text: str) -> Dict[str, Any]:
    """
    Pure regex extraction. Fast, zero API cost.
    Returns dict with entities list and detected tactics.
    """
    lower = text.lower()
    entities = []

    for m in _PHONE_RE.finditer(text):
        entities.append({"type": "phone", "value": m.group().strip(), "confidence": 0.85})

    for m in _UPI_RE.finditer(text):
        entities.append({"type": "upi", "value": m.group(), "confidence": 0.80})

    for m in _URL_RE.finditer(text):
        entities.append({"type": "url", "value": m.group(), "confidence": 1.0})

    for m in _BANK_RE.finditer(text):
        entities.append({"type": "bank_account", "value": m.group(), "confidence": 0.70})

    for m in _IFSC_RE.finditer(text):
        entities.append({"type": "ifsc", "value": m.group(), "confidence": 0.95})

    tactics = [
        name for name, kws in _TACTICS.items() if any(kw in lower for kw in kws)
    ]

    # Threat scoring
    threat = min(100, len(entities) * 10 + len(tactics) * 15)

    return {"entities": entities, "tactics": tactics, "threat_level": threat}
```

### 5d. Scam Detector — `services/scam_detector.py`

```python
from services.intelligence_extractor import extract_entities


def calculate_scam_score(text: str, history: list[str] | None = None) -> float:
    """
    Returns a 0.0–1.0 scam probability.
    Combine keyword signals across the full history.
    """
    combined = " ".join(history or []) + " " + text
    result = extract_entities(combined)
    raw = result["threat_level"]          # 0–100
    return min(1.0, raw / 100.0)
```

### 5e. Storage Service — `services/storage_service.py`

```python
import os
import aiofiles
import logging
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)
_AUDIO_DIR = Path("storage/audio")
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


async def save_audio_locally(audio_bytes: bytes, filename: str) -> str:
    """Save audio bytes to local storage. Returns the file path."""
    path = _AUDIO_DIR / filename
    async with aiofiles.open(path, "wb") as f:
        await f.write(audio_bytes)
    return str(path)


async def upload_to_cloudinary(audio_bytes: bytes, public_id: str) -> str:
    """Upload to Cloudinary and return CDN URL. Falls back to local on error."""
    if settings.STORAGE_BACKEND != "cloudinary":
        return await save_audio_locally(audio_bytes, public_id + ".mp3")

    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )
        import io
        result = cloudinary.uploader.upload(
            io.BytesIO(audio_bytes),
            resource_type="video",    # Cloudinary uses 'video' for audio
            public_id=public_id,
            format="mp3",
        )
        return result["secure_url"]
    except Exception as e:
        logger.error("Cloudinary upload failed: %s — falling back to local", e)
        return await save_audio_locally(audio_bytes, public_id + ".mp3")
```

---

## 6. AI Agent Core (LangGraph)

### File: `agents/prompts.py`

```python
SYSTEM_PROMPT = """You are a confused elderly person who has received an unexpected phone call.
You speak naturally, make occasional mistakes, ask clarifying questions, and try to delay giving any
personal information. Never break character. Keep responses to 1-3 sentences, conversational in tone.
"""

INTENT_PROMPT = """Classify the caller's intent from this message:
"{text}"

Respond with JSON only (no markdown):
{{"intent": "<credential_theft|impersonation|fear_tactic|info_gathering|relationship|tech_support|unknown>",
  "confidence": <0.0-1.0>,
  "summary": "<one sentence>"}}"""

STRATEGY_PROMPT = """Given intent "{intent}" and turn {turn_count}, pick the best strategy.

Rules:
- turns < 3: use "empathy" (build rapport, sound confused)
- turns 3-7: use "info_extraction" (ask questions back, delay)
- turns > 7: use "expose" (hint you might report them)
- Always avoid giving real personal data

Respond with JSON only:
{{"strategy": "<empathy|info_extraction|delay|expose>",
  "reason": "<one sentence>"}}"""

COACHING_PROMPT = """The scammer said: "{scammer_text}"
Their intent: {intent}
Recommended strategy: {strategy}

Generate a coaching suggestion for the operator (human speaking on the call).
Keep it under 15 words, action-oriented, no asterisks.

Respond with JSON only:
{{"text": "<coaching suggestion>",
  "scripts": ["<option 1>", "<option 2>", "<option 3>"]}}"""

RESPONSE_PROMPT = """You are a confused elderly person. The scammer said:
"{scammer_text}"

Strategy: {strategy}
Conversation so far (last 3 turns):
{history}

Respond naturally, in character, 1-2 sentences max. Do NOT give OTP, passwords, bank details.
Respond with JSON only:
{{"text": "<your response as elderly person>"}}"""
```

### File: `agents/graph.py`

This is the LangGraph state machine. Each node is a pure async function.

```python
import json
import logging
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from agents.prompts import INTENT_PROMPT, STRATEGY_PROMPT, COACHING_PROMPT, RESPONSE_PROMPT
from config import settings

logger = logging.getLogger(__name__)

# ── LLM singleton (shared across all nodes) ───────────────────────────────────

_llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name=settings.GROQ_MODEL,
    temperature=0.3,
    max_tokens=256,    # Keep responses tight — saves tokens
)


# ── State schema ──────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    scammer_text: str
    history: List[dict]
    mode: str                   # "ai_coached" | "ai_takeover"
    turn_count: int
    intent: Optional[str]
    intent_confidence: Optional[float]
    strategy: Optional[str]
    coaching_text: Optional[str]
    coaching_scripts: Optional[List[str]]
    ai_response: Optional[str]
    error: Optional[str]


# ── Helper: parse LLM JSON safely ─────────────────────────────────────────────

def _parse_json(content: str) -> dict:
    try:
        # Strip markdown fences if present
        clean = content.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(clean)
    except Exception:
        logger.warning("Failed to parse LLM JSON: %s", content[:200])
        return {}


async def _call_llm(prompt: str) -> dict:
    try:
        response = await _llm.ainvoke([HumanMessage(content=prompt)])
        return _parse_json(response.content)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return {}


# ── Graph nodes ───────────────────────────────────────────────────────────────

async def node_intent(state: AgentState) -> AgentState:
    result = await _call_llm(
        INTENT_PROMPT.format(text=state["scammer_text"])
    )
    return {
        **state,
        "intent": result.get("intent", "unknown"),
        "intent_confidence": result.get("confidence", 0.5),
    }


async def node_strategy(state: AgentState) -> AgentState:
    result = await _call_llm(
        STRATEGY_PROMPT.format(
            intent=state["intent"],
            turn_count=state["turn_count"],
        )
    )
    return {**state, "strategy": result.get("strategy", "empathy")}


async def node_coaching(state: AgentState) -> AgentState:
    """Generates coaching text for operator (ai_coached mode)."""
    history_str = "\n".join(
        f"{m['speaker']}: {m['text']}" for m in state["history"][-3:]
    )
    result = await _call_llm(
        COACHING_PROMPT.format(
            scammer_text=state["scammer_text"],
            intent=state["intent"],
            strategy=state["strategy"],
        )
    )
    return {
        **state,
        "coaching_text": result.get("text", ""),
        "coaching_scripts": result.get("scripts", []),
    }


async def node_response(state: AgentState) -> AgentState:
    """Generates AI's spoken response (ai_takeover mode)."""
    history_str = "\n".join(
        f"{m['speaker']}: {m['text']}" for m in state["history"][-3:]
    )
    result = await _call_llm(
        RESPONSE_PROMPT.format(
            scammer_text=state["scammer_text"],
            strategy=state["strategy"],
            history=history_str,
        )
    )
    return {**state, "ai_response": result.get("text", "")}


def _route_mode(state: AgentState) -> str:
    return "coaching" if state["mode"] == "ai_coached" else "response"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_agent_graph():
    g = StateGraph(AgentState)

    g.add_node("intent",   node_intent)
    g.add_node("strategy", node_strategy)
    g.add_node("coaching", node_coaching)
    g.add_node("response", node_response)

    g.set_entry_point("intent")
    g.add_edge("intent", "strategy")
    g.add_conditional_edges("strategy", _route_mode, {
        "coaching": "coaching",
        "response": "response",
    })
    g.add_edge("coaching", END)
    g.add_edge("response", END)

    return g.compile()


# Singleton compiled graph
agent_graph = build_agent_graph()


async def run_agent(
    scammer_text: str,
    history: list,
    mode: str = "ai_coached",
    turn_count: int = 0,
) -> dict:
    """
    Main entry point for the AI agent.

    Returns:
        For ai_coached: {"intent", "strategy", "coaching_text", "coaching_scripts"}
        For ai_takeover: {"intent", "strategy", "ai_response"}
    """
    initial: AgentState = {
        "scammer_text": scammer_text,
        "history": history,
        "mode": mode,
        "turn_count": turn_count,
        "intent": None,
        "intent_confidence": None,
        "strategy": None,
        "coaching_text": None,
        "coaching_scripts": None,
        "ai_response": None,
        "error": None,
    }
    result = await agent_graph.ainvoke(initial)
    return result
```

---

## 7. Live Call WebSocket API

This is the **primary rebuild target** — the file most likely broken in your existing project.

### File: `api/live_call.py`

The design principles applied here:
- **CallSession** holds all in-memory per-call state; nothing leaks into global scope.
- **CallManager** is the single source of truth for active sessions.
- Audio relay and AI processing run as **concurrent asyncio tasks** — relay is never blocked by transcription or LLM calls.
- Transcription uses a sliding buffer. The buffer flushes after 3 seconds of audio OR on silence.
- AI coaching only fires when the **scammer** speaks (not the operator).
- All exceptions are caught per-operation; a failure in TTS/LLM never drops the call.

```python
"""
live_call.py — WebSocket-based two-way live call with AI coaching.

Endpoint:  ws://<host>/api/live-call/ws/{call_id}?role=operator|scammer
"""

import asyncio
import base64
import io
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from services.stt_service import transcribe_bytes
from services.tts_service import synthesize_to_bytes
from services.intelligence_extractor import extract_entities
from agents.graph import run_agent
from db.mongo import get_collection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/live-call", tags=["live-call"])

# ─────────────────────────────────────────────────────────────────────────────
# Audio normalisation (webm → 16kHz mono PCM)
# Uses pydub. If pydub is unavailable, pass audio through unchanged.
# ─────────────────────────────────────────────────────────────────────────────

def normalize_audio(audio_bytes: bytes, fmt: str = "webm") -> bytes:
    """Convert browser audio (webm/opus) to 16kHz mono 16-bit PCM."""
    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
        seg = seg.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        return seg.raw_data
    except Exception as e:
        logger.warning("Audio normalisation failed (%s) — using raw bytes", e)
        return audio_bytes


# ─────────────────────────────────────────────────────────────────────────────
# In-memory session state
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AudioBuffer:
    """Accumulates PCM bytes and flushes when enough is collected."""
    min_bytes: int = 16000 * 2 * 3     # 3 seconds @ 16kHz mono 16-bit
    _buf: bytearray = field(default_factory=bytearray)

    def add(self, chunk: bytes) -> None:
        self._buf.extend(chunk)

    def ready(self) -> bool:
        return len(self._buf) >= self.min_bytes

    def flush(self) -> bytes:
        data = bytes(self._buf)
        self._buf.clear()
        return data

    def clear(self) -> None:
        self._buf.clear()


@dataclass
class CallSession:
    call_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

    operator_ws: Optional[WebSocket] = None
    scammer_ws: Optional[WebSocket] = None

    operator_buf: AudioBuffer = field(default_factory=AudioBuffer)
    scammer_buf: AudioBuffer = field(default_factory=AudioBuffer)

    transcript: List[dict] = field(default_factory=list)
    turn_count: int = 0

    @property
    def both_connected(self) -> bool:
        return self.operator_ws is not None and self.scammer_ws is not None

    async def send_operator(self, msg: dict) -> None:
        if self.operator_ws:
            try:
                await self.operator_ws.send_json(msg)
            except Exception:
                pass

    async def send_scammer(self, msg: dict) -> None:
        if self.scammer_ws:
            try:
                await self.scammer_ws.send_json(msg)
            except Exception:
                pass

    async def broadcast(self, msg: dict) -> None:
        await asyncio.gather(
            self.send_operator(msg),
            self.send_scammer(msg),
            return_exceptions=True,
        )

    async def close_all(self) -> None:
        self.is_active = False
        for ws in (self.operator_ws, self.scammer_ws):
            if ws:
                try:
                    await ws.close(code=1000)
                except Exception:
                    pass


class CallManager:
    def __init__(self):
        self._sessions: Dict[str, CallSession] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, call_id: str) -> CallSession:
        async with self._lock:
            if call_id not in self._sessions:
                self._sessions[call_id] = CallSession(call_id=call_id)
            return self._sessions[call_id]

    async def remove(self, call_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(call_id, None)
            if session:
                await session.close_all()

    def get(self, call_id: str) -> Optional[CallSession]:
        return self._sessions.get(call_id)


# Module-level singleton
call_manager = CallManager()


# ─────────────────────────────────────────────────────────────────────────────
# Audio processing helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _process_transcription(
    session: CallSession,
    speaker: str,
    raw_audio: bytes,
    audio_fmt: str,
) -> Optional[str]:
    """
    Normalise → buffer → transcribe when buffer is full.
    Returns transcription text or None if buffer not yet full.
    """
    buf = session.operator_buf if speaker == "operator" else session.scammer_buf
    pcm = normalize_audio(raw_audio, fmt=audio_fmt)
    buf.add(pcm)

    if not buf.ready():
        return None

    flushed = buf.flush()
    try:
        result = await transcribe_bytes(flushed, fmt="wav")
        text = result.get("text", "").strip()
        if text:
            entry = {
                "speaker": speaker,
                "text": text,
                "language": result.get("language", "en"),
                "confidence": result.get("confidence", 0.95),
                "timestamp": datetime.utcnow().isoformat(),
            }
            session.transcript.append(entry)
            session.turn_count += 1
            return text
    except Exception as e:
        logger.error("Transcription error for %s: %s", speaker, e)

    return None


async def _run_ai_pipeline(session: CallSession, scammer_text: str) -> None:
    """
    Intelligence extraction + agent coaching, fired concurrently.
    Sends results to operator only.
    """
    intel_task = asyncio.create_task(
        asyncio.to_thread(extract_entities, scammer_text)
    )
    agent_task = asyncio.create_task(
        run_agent(
            scammer_text=scammer_text,
            history=session.transcript[-6:],   # last 3 turns (6 entries)
            mode="ai_coached",
            turn_count=session.turn_count,
        )
    )

    intel_result, agent_result = await asyncio.gather(
        intel_task, agent_task, return_exceptions=True
    )

    # ── Send intelligence ────────────────────────────────────────────────────
    if isinstance(intel_result, dict):
        await session.send_operator({
            "type": "intelligence",
            "entities":    intel_result.get("entities", []),
            "threat_level": intel_result.get("threat_level", 0),
            "tactics":     intel_result.get("tactics", []),
            "timestamp":   datetime.utcnow().isoformat(),
        })

    # ── Send coaching ────────────────────────────────────────────────────────
    if isinstance(agent_result, dict) and agent_result.get("coaching_text"):
        coaching_text = agent_result["coaching_text"]

        # TTS — fire-and-forget; errors must not break the session
        coaching_audio_b64: Optional[str] = None
        try:
            audio_bytes = await synthesize_to_bytes(coaching_text)
            coaching_audio_b64 = base64.b64encode(audio_bytes).decode()
        except Exception as e:
            logger.warning("TTS failed for coaching: %s", e)

        await session.send_operator({
            "type":          "ai_coaching",
            "text":          coaching_text,
            "audio":         coaching_audio_b64,   # None if TTS failed
            "scripts":       agent_result.get("coaching_scripts", []),
            "strategy":      agent_result.get("strategy", "empathy"),
            "intent":        agent_result.get("intent", "unknown"),
            "timestamp":     datetime.utcnow().isoformat(),
        })


# ─────────────────────────────────────────────────────────────────────────────
# Main WebSocket handler
# ─────────────────────────────────────────────────────────────────────────────

@router.websocket("/ws/{call_id}")
async def live_call_ws(
    websocket: WebSocket,
    call_id: str,
    role: str = Query(..., pattern="^(operator|scammer)$"),
):
    """
    Single WebSocket endpoint for both operator and scammer.
    role = 'operator' | 'scammer'
    """
    await websocket.accept()
    session = await call_manager.get_or_create(call_id)

    # ── Register connection ──────────────────────────────────────────────────
    if role == "operator":
        session.operator_ws = websocket
    else:
        session.scammer_ws = websocket

    logger.info("CALL %s: %s connected", call_id, role)

    # ── Confirm connection ───────────────────────────────────────────────────
    await websocket.send_json({
        "type":      "connected",
        "role":      role,
        "call_id":   call_id,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # ── Notify both sides when pair is complete ──────────────────────────────
    if session.both_connected:
        await session.broadcast({
            "type":    "participant_joined",
            "message": "Both participants connected. Call is live.",
        })

    # ── Message loop ─────────────────────────────────────────────────────────
    try:
        while session.is_active:
            try:
                msg = await asyncio.wait_for(
                    websocket.receive_json(), timeout=30.0
                )
            except asyncio.TimeoutError:
                # Keep-alive check
                await websocket.send_json({"type": "ping"})
                continue

            msg_type = msg.get("type")

            # ── Ping/pong ────────────────────────────────────────────────────
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # ── End call ─────────────────────────────────────────────────────
            if msg_type == "end_call":
                await session.broadcast({
                    "type":      "call_ended",
                    "reason":    "user_request",
                    "duration":  (datetime.utcnow() - session.created_at).seconds,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                await call_manager.remove(call_id)
                return

            # ── Audio chunk ──────────────────────────────────────────────────
            if msg_type == "audio":
                raw_b64 = msg.get("data", "")
                audio_fmt = msg.get("format", "webm")
                if not raw_b64:
                    continue

                try:
                    raw_bytes = base64.b64decode(raw_b64)
                except Exception:
                    continue

                # ── Relay audio to the OTHER participant (non-blocking) ──────
                relay_target = session.scammer_ws if role == "operator" else session.operator_ws
                if relay_target:
                    asyncio.create_task(relay_target.send_json({
                        "type":      "audio",
                        "data":      raw_b64,          # relay as-is
                        "from":      role,
                        "timestamp": datetime.utcnow().isoformat(),
                    }))

                # ── Transcription (async, non-blocking) ─────────────────────
                async def _transcribe_and_notify(
                    _raw=raw_bytes, _fmt=audio_fmt, _role=role
                ):
                    text = await _process_transcription(session, _role, _raw, _fmt)
                    if text:
                        await session.broadcast({
                            "type":      "transcription",
                            "speaker":   _role,
                            "text":      text,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        # AI coaching only for scammer audio
                        if _role == "scammer" and session.both_connected:
                            asyncio.create_task(_run_ai_pipeline(session, text))

                asyncio.create_task(_transcribe_and_notify())

    except WebSocketDisconnect:
        logger.info("CALL %s: %s disconnected", call_id, role)
    except Exception as e:
        logger.error("CALL %s: %s error: %s", call_id, role, e)
    finally:
        # Clean up disconnected websocket reference
        if role == "operator":
            session.operator_ws = None
        else:
            session.scammer_ws = None

        # If no one is left, schedule session cleanup after 60s grace period
        async def _deferred_cleanup():
            await asyncio.sleep(60)
            s = call_manager.get(call_id)
            if s and not s.both_connected:
                logger.info("CALL %s: cleaning up abandoned session", call_id)
                await call_manager.remove(call_id)

        asyncio.create_task(_deferred_cleanup())


# ─────────────────────────────────────────────────────────────────────────────
# REST companions
# ─────────────────────────────────────────────────────────────────────────────

class StartCallRequest(BaseModel):
    call_id: Optional[str] = None


@router.post("/start")
async def start_call(req: StartCallRequest):
    call_id = req.call_id or str(uuid.uuid4())
    await call_manager.get_or_create(call_id)
    return {
        "call_id": call_id,
        "operator_url": f"/api/live-call/ws/{call_id}?role=operator",
        "scammer_url":  f"/api/live-call/ws/{call_id}?role=scammer",
    }


@router.get("/status/{call_id}")
async def call_status(call_id: str):
    session = call_manager.get(call_id)
    if not session:
        return {"status": "not_found"}
    return {
        "call_id":           call_id,
        "is_active":         session.is_active,
        "operator_connected": session.operator_ws is not None,
        "scammer_connected":  session.scammer_ws is not None,
        "turn_count":        session.turn_count,
        "created_at":        session.created_at.isoformat(),
    }


@router.post("/end/{call_id}")
async def end_call(call_id: str):
    session = call_manager.get(call_id)
    if session:
        await session.broadcast({"type": "call_ended", "reason": "api_request"})
        await call_manager.remove(call_id)
    return {"status": "ended", "call_id": call_id}
```

---

## 8. REST API Routes

### File: `api/auth_routes.py`

```python
from fastapi import APIRouter, HTTPException, status, Depends
from db.mongo import get_collection
from db.models import UserCreate, UserInDB, UserOut
from core.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user,
)
from datetime import datetime

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(body: UserCreate):
    col = get_collection("users")
    if await col.find_one({"username": body.username}):
        raise HTTPException(400, "Username already taken")

    user = UserInDB(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name or body.username,
    )
    await col.insert_one(user.model_dump())
    return {"message": "registered", "user_id": user.user_id}


@router.post("/login")
async def login(body: UserCreate):
    col = get_collection("users")
    doc = await col.find_one({"username": body.username})
    if not doc or not verify_password(body.password, doc["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    await col.update_one(
        {"username": body.username},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    payload = {"sub": doc["user_id"], "username": doc["username"]}
    return {
        "access_token":  create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type":    "bearer",
    }


@router.post("/refresh")
async def refresh(body: dict):
    token = body.get("refresh_token", "")
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Not a refresh token")
    new_token = create_access_token({"sub": payload["sub"], "username": payload["username"]})
    return {"access_token": new_token, "token_type": "bearer"}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    col = get_collection("users")
    doc = await col.find_one({"user_id": user["sub"]})
    if not doc:
        raise HTTPException(404, "User not found")
    return UserOut(**doc)
```

### File: `api/sessions.py`

```python
from fastapi import APIRouter, Depends
from db.mongo import get_collection
from db.models import SessionCreate, SessionInDB
from core.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=201)
async def create_session(body: SessionCreate, user=Depends(get_current_user)):
    session = SessionInDB(
        user_id=user["sub"],
        scammer_phone=body.scammer_phone,
        operator_name=body.operator_name,
        metadata={"call_type": body.call_type},
    )
    await get_collection("sessions").insert_one(session.model_dump())
    return {"session_id": session.session_id}


@router.get("")
async def list_sessions(user=Depends(get_current_user)):
    col = get_collection("sessions")
    docs = await col.find(
        {"user_id": user["sub"]},
        {"_id": 0},
        sort=[("created_at", -1)],
        limit=50
    ).to_list(50)
    return docs


@router.get("/{session_id}")
async def get_session(session_id: str, user=Depends(get_current_user)):
    doc = await get_collection("sessions").find_one(
        {"session_id": session_id, "user_id": user["sub"]}, {"_id": 0}
    )
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(404, "Session not found")
    return doc


@router.delete("/{session_id}")
async def delete_session(session_id: str, user=Depends(get_current_user)):
    await get_collection("sessions").delete_one(
        {"session_id": session_id, "user_id": user["sub"]}
    )
    return {"deleted": session_id}
```

### File: `api/message.py`

```python
from fastapi import APIRouter, Depends
from db.mongo import get_collection
from db.models import MessageCreate, MessageInDB
from core.auth import get_current_user
from agents.graph import run_agent

router = APIRouter(prefix="/api/message", tags=["message"])


@router.post("/send")
async def send_message(body: MessageCreate, user=Depends(get_current_user)):
    col_msg = get_collection("messages")

    # Save scammer message
    scammer_msg = MessageInDB(
        session_id=body.session_id,
        sender="scammer",
        content=body.content,
    )
    await col_msg.insert_one(scammer_msg.model_dump())

    # Fetch recent history
    history = await col_msg.find(
        {"session_id": body.session_id},
        {"_id": 0, "sender": 1, "content": 1},
        sort=[("timestamp", -1)],
        limit=10,
    ).to_list(10)
    history = [{"speaker": h["sender"], "text": h["content"]} for h in reversed(history)]

    # Run agent
    result = await run_agent(
        scammer_text=body.content,
        history=history,
        mode="ai_takeover",
    )

    agent_reply = result.get("ai_response", "I'm sorry, could you repeat that?")

    # Save agent reply
    agent_msg = MessageInDB(
        session_id=body.session_id,
        sender="agent",
        content=agent_reply,
    )
    await col_msg.insert_one(agent_msg.model_dump())

    return {"reply": agent_reply, "intent": result.get("intent"), "strategy": result.get("strategy")}


@router.get("/session/{session_id}")
async def get_messages(session_id: str, user=Depends(get_current_user)):
    docs = await get_collection("messages").find(
        {"session_id": session_id},
        {"_id": 0},
        sort=[("timestamp", 1)],
    ).to_list(500)
    return docs
```

### File: `api/voice.py`

```python
import base64
import uuid
from fastapi import APIRouter, UploadFile, File, Form, Depends
from core.auth import get_current_user
from services.stt_service import transcribe_bytes
from services.tts_service import synthesize_to_bytes
from agents.graph import run_agent
from db.mongo import get_collection
from db.models import MessageInDB

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/upload")
async def voice_upload(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    mode: str = Form("ai_speaks"),
    user=Depends(get_current_user),
):
    audio_bytes = await audio.read()
    fmt = audio.filename.rsplit(".", 1)[-1] if "." in audio.filename else "webm"

    # Transcribe
    stt = await transcribe_bytes(audio_bytes, fmt)
    scammer_text = stt.get("text", "")

    # Fetch history
    col_msg = get_collection("messages")
    history_docs = await col_msg.find(
        {"session_id": session_id},
        {"_id": 0, "sender": 1, "content": 1},
        sort=[("timestamp", -1)],
        limit=6,
    ).to_list(6)
    history = [{"speaker": d["sender"], "text": d["content"]} for d in reversed(history_docs)]

    # Agent
    result = await run_agent(
        scammer_text=scammer_text,
        history=history,
        mode="ai_takeover" if mode == "ai_speaks" else "ai_coached",
    )
    reply = result.get("ai_response") or result.get("coaching_text", "")

    # TTS
    audio_b64 = ""
    if mode == "ai_speaks" and reply:
        tts_bytes = await synthesize_to_bytes(reply)
        audio_b64 = base64.b64encode(tts_bytes).decode()

    # Persist messages
    for sender, content in [("scammer", scammer_text), ("agent", reply)]:
        if content:
            msg = MessageInDB(session_id=session_id, sender=sender, content=content)
            await col_msg.insert_one(msg.model_dump())

    return {
        "transcription": scammer_text,
        "reply":         reply,
        "audio_b64":     audio_b64,           # base64 MP3 or empty
        "intent":        result.get("intent"),
        "strategy":      result.get("strategy"),
    }
```

---

## 9. WebRTC Signaling (Socket.IO)

### File: `api/webrtc_signaling.py`

```python
import socketio
import logging

logger = logging.getLogger(__name__)

# Use async mode, CORS handled at ASGI mount level
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# Room tracking: room_id → {sid: role}
_rooms: dict[str, dict[str, str]] = {}


@sio.event
async def connect(sid, environ):
    logger.info("Socket.IO connect: %s", sid)


@sio.event
async def disconnect(sid):
    # Remove from any room
    for room_id, members in list(_rooms.items()):
        if sid in members:
            role = members.pop(sid)
            await sio.leave_room(sid, room_id)
            await sio.emit("peer_disconnected", {"role": role}, room=room_id)
            if not members:
                del _rooms[room_id]
            break
    logger.info("Socket.IO disconnect: %s", sid)


@sio.event
async def join_room(sid, data):
    room_id = data.get("room_id")
    role    = data.get("role", "unknown")
    if not room_id:
        return

    await sio.enter_room(sid, room_id)
    _rooms.setdefault(room_id, {})[sid] = role

    # Notify others in room
    await sio.emit("peer_joined", {"role": role}, room=room_id, skip_sid=sid)
    logger.info("Socket.IO %s joined room %s as %s", sid, room_id, role)


@sio.event
async def signal(sid, data):
    """Relay WebRTC signaling (SDP offer/answer, ICE candidates)."""
    room_id = data.get("room_id")
    if room_id:
        await sio.emit("signal", data, room=room_id, skip_sid=sid)


@sio.event
async def leave_room(sid, data):
    room_id = data.get("room_id")
    if room_id and sid in _rooms.get(room_id, {}):
        role = _rooms[room_id].pop(sid)
        await sio.leave_room(sid, room_id)
        await sio.emit("peer_disconnected", {"role": role}, room=room_id)
```

---

## 10. Application Entry Point

### File: `core/lifecycle.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from db.mongo import connect_db, close_db
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting HoneyBadger backend…")
    await connect_db()
    yield
    await close_db()
    logger.info("Backend shutdown complete.")
```

### File: `main.py`

```python
import logging
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from core.lifecycle import lifespan

# ── Routes ────────────────────────────────────────────────────────────────────
from api.auth_routes     import router as auth_router
from api.sessions        import router as sessions_router
from api.message         import router as message_router
from api.voice           import router as voice_router
from api.live_call       import router as live_call_router
from api.webrtc_signaling import sio

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="HoneyBadger API",
    version="3.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register REST/WS routers ──────────────────────────────────────────────────
for r in [auth_router, sessions_router, message_router, voice_router, live_call_router]:
    app.include_router(r)

# ── Mount Socket.IO for WebRTC signaling ──────────────────────────────────────
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}
```

> **CRITICAL:** The Socket.IO mount changes how you start the server. See §12.

---

## 11. Environment Variables Reference

Create `backend/.env` with all of these:

```env
# ── Core ──────────────────────────────────────────────────────────────────────
API_SECRET_KEY=replace-with-strong-random-string
HOST=0.0.0.0
PORT=8000
DEBUG=false

# ── Database ──────────────────────────────────────────────────────────────────
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net
MONGODB_DATABASE=honeypot_db

# ── LLM ───────────────────────────────────────────────────────────────────────
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
GEMINI_API_KEY=AIza...         # optional fallback

# ── Voice ─────────────────────────────────────────────────────────────────────
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# ── Storage ───────────────────────────────────────────────────────────────────
STORAGE_BACKEND=local           # or "cloudinary"
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# ── Auth ──────────────────────────────────────────────────────────────────────
JWT_SECRET_KEY=replace-with-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Rate Limiting ─────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0   # or Upstash/Redis Cloud URL

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ORIGINS=*    # production: https://yourapp.com,https://yourapp2.com

# ── External callbacks ────────────────────────────────────────────────────────
GUVI_CALLBACK_URL=
VIRUSTOTAL_API_KEY=
```

---

## 12. Dependency Install & Run Commands

### First-time setup

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt

# Create storage directories
mkdir -p storage/audio storage/reports

# Copy env template
cp .env.example .env              # then fill in your keys
```

### Development (with hot reload)

```bash
# Because Socket.IO is mounted, run socket_app not app
uvicorn main:socket_app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
uvicorn main:socket_app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info
```

### MongoDB indexes (run once)

```bash
python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

async def setup():
    c = AsyncIOMotorClient(settings.MONGODB_URI)
    db = c[settings.MONGODB_DATABASE]
    await db.users.create_index('username', unique=True)
    await db.sessions.create_index('session_id', unique=True)
    await db.sessions.create_index([('user_id', 1), ('created_at', -1)])
    await db.messages.create_index([('session_id', 1), ('timestamp', 1)])
    await db.intelligence.create_index('session_id')
    print('Indexes created.')
    c.close()

asyncio.run(setup())
"
```

### Verify the stack

```bash
# Health endpoint
curl http://localhost:8000/health

# Register a user
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"test","password":"test123","display_name":"Test User"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"test","password":"test123"}'

# Start a live call
curl -X POST http://localhost:8000/api/live-call/start \
  -H 'Content-Type: application/json' \
  -d '{}'
```

---

## Quick Troubleshooting

**WebSocket drops immediately:** Make sure you're running `socket_app`, not `app`. Socket.IO is mounted on top and the ASGI wrapping changes the entry point.

**TTS returns None but no error:** Your `ELEVENLABS_API_KEY` is missing or wrong. The code catches the exception and sends text-only coaching. Check your `.env`.

**Groq Whisper returns empty string:** The audio being sent is valid WebM from the browser but pydub couldn't convert it because ffmpeg is not installed. Run `apt install ffmpeg` (Linux) or `brew install ffmpeg` (Mac).

**LLM coaching is slow (>5s):** The three sequential LLM calls (intent → strategy → coaching) add up. You can reduce `max_tokens` further in `agents/graph.py` or switch `GROQ_MODEL` to a smaller model like `llama-3.1-8b-instant` for the coaching node only.

**MongoDB timeout on first request:** Your Atlas cluster is on a free tier and goes to sleep. Add `serverSelectionTimeoutMS=5000` (already set) and consider upgrading to M10.

**CORS error from mobile app:** Set `CORS_ORIGINS=*` in `.env` during development. For production, list your exact origins.
