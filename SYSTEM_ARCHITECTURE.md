# HoneyBadger System Architecture

> **Comprehensive Architecture Document**  
> Version 1.0 | February 2026

---

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Live Call Architecture (Detailed)](#live-call-architecture-detailed)
6. [Data Flow & Communication Patterns](#data-flow--communication-patterns)
7. [Technology Stack](#technology-stack)
8. [Database Schema](#database-schema)
9. [Security & Authentication](#security--authentication)
10. [Deployment Architecture](#deployment-architecture)

---

## System Overview

**HoneyBadger** is an AI-powered honeypot system designed to detect, engage, and collect intelligence from scam attempts. The system features:

- **Real-time voice/text conversations** with scammers
- **AI agent** that mimics victim behavior using LangGraph
- **Live call functionality** with operator-scammer real-time communication
- **Intelligence extraction** (phone numbers, URLs, tactics, entities)
- **Voice cloning** for realistic operator impersonation
- **Evidence collection** with audio storage and transcription
- **Threat analysis** and reporting

---

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                          │
│  React + Vite + WebSocket Client + MediaRecorder + WebRTC      │
│                                                                  │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │  Dashboard   │ Voice Player │  Live Call   │  Playground  │ │
│  │              │              │  WebSocket   │              │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
└────────────────────────────────────────────────────────────────┘
                              ↕ HTTP/WS/WebRTC
┌────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                        │
│                FastAPI + Socket.IO + CORS + Rate Limiting       │
│                                                                  │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │ REST APIs    │  WebSocket   │  Socket.IO   │  Auth        │ │
│  │ (/api)       │  (Live Call) │  (WebRTC)    │  (JWT)       │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
└────────────────────────────────────────────────────────────────┘
                              ↕
┌────────────────────────────────────────────────────────────────┐
│                        BUSINESS LOGIC LAYER                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    AGENT CORE (LangGraph)                 │  │
│  │  Intent Analysis → Strategy → Response → Humanization    │  │
│  │  (Groq LLM + Gemini Fallback)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↕                                  │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │   Voice      │  Intelligence│   Scam       │   Report     │ │
│  │   Services   │   Extractor  │   Detector   │   Generator  │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
└────────────────────────────────────────────────────────────────┘
                              ↕
┌────────────────────────────────────────────────────────────────┐
│                        SERVICES LAYER                           │
│                                                                  │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │  ElevenLabs  │  Whisper STT │  Cloudinary  │  Storage     │ │
│  │  TTS         │  (Faster)    │  Audio Store │  Service     │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │  Voice Clone │  Audio       │  Callback    │  VirusTotal  │ │
│  │  Service     │  Processor   │  Service     │  Scanner     │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
└────────────────────────────────────────────────────────────────┘
                              ↕
┌────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    MongoDB Atlas                          │  │
│  │  Sessions | Messages | Intelligence | VoiceChunks        │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Cloudinary CDN (Audio Files)                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                Redis (Rate Limiting Cache)                │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

---

## Backend Architecture

### Directory Structure

```
honeypot/backend/
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration with pydantic-settings
├── requirements.txt           # Python dependencies
│
├── core/                      # Core system utilities
│   ├── auth.py               # API key verification, JWT auth
│   └── lifecycle.py          # Session lifecycle management
│
├── db/                       # Database layer
│   ├── mongo.py              # MongoDB connection singleton
│   └── models.py             # Pydantic models (Session, Message, Intelligence)
│
├── api/                      # REST & WebSocket endpoints
│   ├── auth_routes.py        # Authentication endpoints
│   ├── sessions.py           # Session CRUD operations
│   ├── message.py            # Message handling
│   ├── voice.py              # Voice upload/transcription/response
│   ├── live_call.py          # Two-way live call WebSocket API
│   ├── live_takeover.py      # Live takeover mode WebSocket API
│   ├── webrtc_signaling.py   # WebRTC signaling via Socket.IO
│   ├── voice_clone.py        # Voice cloning endpoints
│   ├── elevenlabs_routes.py  # ElevenLabs voice management
│   ├── sms_evidence.py       # SMS evidence collection
│   └── testing.py            # Testing & debugging endpoints
│
├── agents/                   # AI Agent Core (LangGraph)
│   ├── graph.py              # LangGraph workflow definition
│   ├── prompts.py            # System, intent, strategy, humanizer prompts
│   ├── persona.py            # Persona management (elderly victim, etc.)
│   ├── memory.py             # Agent memory & context management
│   ├── voice_adapter.py      # Voice I/O adapter for agent
│   └── speech_naturalizer.py # Makes responses sound natural for voice
│
├── services/                 # External service integrations
│   ├── elevenlabs_service.py # ElevenLabs TTS API (primary)
│   ├── tts_service.py        # Multi-engine TTS (ElevenLabs, Piper, gTTS, pyttsx3)
│   ├── stt_service.py        # Faster-Whisper STT engine
│   ├── audio_processor.py    # Audio format conversion & validation
│   ├── intelligence_extractor.py # Extract entities from conversations
│   ├── scam_detector.py      # Detect scam patterns & calculate threat score
│   ├── storage_service.py    # Audio file storage (Cloudinary/MinIO/local)
│   ├── cloudinary_service.py # Cloudinary CDN integration
│   └── callback.py           # External callback notifications
│
├── features/                 # Feature modules
│   └── live_takeover/        # Live takeover feature package
│       ├── intelligence_pipeline.py  # Real-time intelligence extraction
│       ├── report_generator.py       # Generate session reports
│       ├── session_manager.py        # Manage live takeover sessions
│       ├── streaming_stt.py          # Streaming STT with buffering
│       ├── takeover_agent.py         # Agent for takeover mode
│       ├── takeover_prompts.py       # Prompts for takeover scenarios
│       ├── url_scanner.py            # URL threat scanning
│       └── voice_clone_service.py    # Voice cloning management
│
└── storage/                  # Local file storage
    ├── audio/                # Temporary audio files
    └── reports/              # Generated reports (PDF, CSV, JSON)
```

### Key Backend Components

#### 1. **FastAPI Application (`main.py`)**
- Application entry point with lifespan management
- CORS configuration for cross-origin requests
- Rate limiting using SlowAPI (Redis-backed)
- Global exception handling
- Router registration for all API endpoints
- Socket.IO mounting for WebRTC signaling

#### 2. **Agent Core (`agents/graph.py`)**
LangGraph-based AI agent with 5-node workflow:

```python
Intent Analysis → Strategy Planning → Response Draft → Humanization → Final Response
```

**Node Descriptions:**
- **Intent Node**: Analyzes scammer's intent (urgency, fear, greed)
- **Strategy Node**: Plans agent response strategy (delay, info extract, empathy)
- **Draft Node**: Generates raw response based on strategy
- **Humanizer Node**: Makes response natural for speech (um, hmm, pauses)
- **Final Node**: Returns polished response with metadata

#### 3. **Voice Adapter (`agents/voice_adapter.py`)**
Bridges voice I/O with the agent:
- Processes scammer audio → STT → Agent → TTS → Audio response
- Primary TTS: **ElevenLabs** (with fallback to system TTS)
- STT: **Faster-Whisper** (tiny model on CPU)
- **Emotion preservation**: Maintains emotional context in voice

#### 4. **Services Layer**

**ElevenLabs Service** (`services/elevenlabs_service.py`)
- Singleton service with free voice presets (Rachel, Domi, Bella, etc.)
- API-based synthesis with Cloudinary upload
- Returns both `audio_path` (URL) and `local_path` (file) for flexible usage

**TTS Service** (`services/tts_service.py`)
- Multi-engine fallback chain: **ElevenLabs → Piper → gTTS → pyttsx3**
- `synthesize()`: Saves to file with Cloudinary upload
- `synthesize_to_bytes()`: Returns raw MP3 bytes for WebSocket streaming

**STT Service** (`services/stt_service.py`)
- Faster-Whisper integration (tiny model, CPU-optimized)
- Language detection and transcription confidence scoring
- Format conversion support (wav, mp3, webm)

**Intelligence Extractor** (`services/intelligence_extractor.py`)
- Regex + LLM-based entity extraction
- Extracts: phone numbers, URLs, UPI IDs, bank accounts, keywords, tactics
- Updates session intelligence in real-time

**Scam Detector** (`services/scam_detector.py`)
- Multi-stage scam detection:
  1. Keyword matching (urgent, lottery, bank OTP, etc.)
  2. Pattern recognition (money requests, threats)
  3. LLM-based verification
- Calculates threat score (0-1 scale)

---

## Frontend Architecture

### Directory Structure

```
honeypot/frontend/
├── index.html               # HTML entry point
├── package.json             # Node dependencies
├── vite.config.js           # Vite build configuration
├── tailwind.config.js       # Tailwind CSS configuration
│
├── src/
│   ├── App.jsx              # Main React app with routing
│   ├── main.jsx             # React DOM entry
│   ├── index.css            # Global styles & Tailwind imports
│   │
│   ├── pages/               # Page-level components
│   │   ├── LandingPage.jsx          # Landing page
│   │   ├── Dashboard.jsx            # Session dashboard
│   │   ├── SessionView.jsx          # Individual session details
│   │   ├── Playground.jsx           # Text chat playground
│   │   ├── VoicePlayground.jsx      # Voice interaction playground
│   │   ├── LiveCall.jsx             # Live call WebSocket UI
│   │   ├── LiveCallWebRTC.jsx       # WebRTC-based live call
│   │   ├── LiveTakeoverMode.jsx     # Live takeover interface
│   │   ├── VoiceCloneSetup.jsx      # Voice cloning setup
│   │   ├── CallStarter.jsx          # Call initiation page
│   │   └── MobileOptimizedLiveCall.jsx  # Mobile-optimized call UI
│   │
│   ├── components/          # Reusable UI components
│   │   ├── Navbar.jsx               # Navigation bar
│   │   ├── MobileNavbar.jsx         # Mobile navigation
│   │   ├── VoiceRecorder.jsx        # Audio recording component
│   │   ├── VoicePlayer.jsx          # Audio playback component
│   │   ├── InstallPWAButton.jsx     # PWA install prompt
│   │   ├── OfflineIndicator.jsx     # Offline status indicator
│   │   └── MobileOptimizedLiveCall.jsx  # Mobile call optimizations
│   │
│   └── utils/               # Utility functions
│       └── pwa.js           # PWA detection & utilities
│
├── public/                  # Static assets
│   ├── manifest.json        # PWA manifest
│   └── icons/               # App icons
│
├── android/                 # Android Capacitor build
└── ios/                     # iOS Capacitor build
```

### Key Frontend Components

#### 1. **VoicePlayground.jsx**
Voice interaction playground with two modes:
- **AI Speaks Mode**: Record → Upload → AI responds with voice
- **AI Suggests Mode**: Record → Upload → AI suggests text responses

**Features:**
- MediaRecorder API for audio capture
- Audio format: `audio/webm` (browser native)
- Real-time transcription display
- Audio playback with VoicePlayer component
- Session history with message list

**Flow:**
```
User clicks Record → MediaRecorder starts
User clicks Stop → Upload to /api/voice/upload
Backend processes → Returns transcription + AI reply + audioUrl
VoicePlayer plays response audio from Cloudinary CDN
```

#### 2. **LiveCall.jsx**
Two-way real-time voice call interface:

**Roles:**
- **Operator**: Human operator engaging with scammer
- **Scammer**: Scammer side (simulated or real)

**Features:**
- WebSocket connection to `/api/live-call/ws/{call_id}?role={operator|scammer}`
- Real-time audio streaming (base64-encoded chunks)
- Live transcription for both sides
- AI coaching suggestions for operator
- Intelligence display (entities, threat level, tactics)
- Audio queue with Web Audio API playback

**UI Sections:**
- Call controls (mic on/off, end call)
- Live transcript display
- AI coaching panel (for operator)
- Intelligence dashboard (entities, tactics, threat level)

#### 3. **VoiceRecorder.jsx**
Reusable audio recording component:

```jsx
<VoiceRecorder 
  onRecordingComplete={(audioBlob) => {}} 
  isRecording={bool}
  onToggleRecording={() => {}}
/>
```

**Features:**
- MediaRecorder API integration
- Waveform visualization (optional)
- Real-time duration display
- Audio blob export

#### 4. **VoicePlayer.jsx**
Audio playback component with controls:

```jsx
<VoicePlayer 
  audioUrl="https://cloudinary.com/.../audio.mp3"
  onPlayComplete={() => {}}
/>
```

**Features:**
- Play/pause controls
- Progress bar with seek
- Duration display
- Smart URL handling (Cloudinary vs local API paths)

---

## Live Call Architecture (Detailed)

### Overview

The **Live Call** feature enables real-time two-way voice communication between an operator and a scammer, with AI-powered assistance. There are **two implementations**:

1. **WebSocket-based Live Call** (`live_call.py`) - Current production implementation
2. **WebRTC-based Live Call** (`live_call_webrtc.py`, `webrtc_signaling.py`) - P2P alternative

### WebSocket-Based Live Call Architecture

#### System Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (LiveCall.jsx)                          │
│                                                                           │
│  ┌──────────────────┐                            ┌──────────────────┐   │
│  │  Operator View   │                            │  Scammer View    │   │
│  │                  │                            │                  │   │
│  │  - Mic Control   │                            │  - Mic Control   │   │
│  │  - AI Coaching   │                            │  - Transcription │   │
│  │  - Intelligence  │                            │  - Audio Player  │   │
│  │  - Transcript    │                            │  - Status        │   │
│  └──────────────────┘                            └──────────────────┘   │
│         ↕ WebSocket                                    ↕ WebSocket      │
└─────────────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                    BACKEND (live_call.py - CallManager)                  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      CallSession (In-Memory State)                  │ │
│  │                                                                     │ │
│  │  - call_id: str                                                    │ │
│  │  - operator_ws: WebSocket                                          │ │
│  │  - scammer_ws: WebSocket                                           │ │
│  │  - operator_transcriber: StreamingTranscriber                      │ │
│  │  - scammer_transcriber: StreamingTranscriber                       │ │
│  │  - normalizer: AudioNormalizer                                     │ │
│  │  - transcript: List[dict]                                          │ │
│  │  - entities, threat_level, tactics                                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌──────────────────┐         ┌──────────────────┐                      │
│  │  Audio Pipeline  │         │   AI Pipeline    │                      │
│  │                  │         │                  │                      │
│  │  1. Receive      │         │  1. Transcribe   │                      │
│  │  2. Normalize    │         │  2. Intelligence │                      │
│  │  3. Buffer       │         │  3. Agent Reply  │                      │
│  │  4. Transcribe   │         │  4. TTS (Eleven) │                      │
│  │  5. Relay        │         │  5. Send Coaching│                      │
│  └──────────────────┘         └──────────────────┘                      │
└─────────────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                            SERVICES LAYER                                │
│                                                                           │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐          │
│  │  Faster      │  ElevenLabs  │  Intelligence│   Takeover   │          │
│  │  Whisper STT │  TTS         │  Pipeline    │   Agent      │          │
│  └──────────────┴──────────────┴──────────────┴──────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Data Flow - Audio Routing

**Operator Speaks:**
```
1. Operator mic → MediaRecorder → audio chunks (webm)
2. Frontend: base64 encode → WebSocket send {"type": "audio", "data": base64}
3. Backend: receive in operator WebSocket handler
4. Decode base64 → Normalize audio → Buffer
5. StreamingTranscriber (Faster-Whisper) → Transcription
6. Send transcription to BOTH operator & scammer WebSockets
   {"type": "transcription", "speaker": "operator", "text": "..."}
7. Audio relay: base64 encode normalized audio → Send to scammer WebSocket
   {"type": "audio", "data": base64, "from": "operator"}
8. Scammer frontend: decode → play via Web Audio API
```

**Scammer Speaks:**
```
1. Scammer mic → MediaRecorder → audio chunks (webm)
2. Frontend: base64 encode → WebSocket send {"type": "audio", "data": base64}
3. Backend: receive in scammer WebSocket handler
4. Decode base64 → Normalize audio → Buffer
5. StreamingTranscriber → Transcription
6. Send transcription to BOTH operator & scammer WebSockets
7. Audio relay to operator WebSocket
8. Operator frontend: play audio
9. PARALLEL: Intelligence extraction + AI coaching generation
```

#### AI Coaching Flow (Operator Side Only)

```
Scammer audio received
↓
Transcription complete
↓
Intelligence Pipeline (parallel):
  - Extract entities (phone, URL, UPI, bank account)
  - Detect tactics (urgency, fear, authority, etc.)
  - Calculate threat level
↓
Takeover Agent (LangGraph):
  - Analyze scammer intent
  - Generate coaching suggestions
  - Strategy recommendations
↓
TTS Service (ElevenLabs):
  - Synthesize coaching audio
  - Upload to Cloudinary (optional)
↓
Send to Operator WebSocket:
{
  "type": "ai_coaching",
  "text": "Ask for their bank details to build trust",
  "audio": base64_audio_data,
  "strategy": "information_extraction",
  "threat_level": 0.75
}
↓
Operator frontend:
  - Display coaching text
  - Play audio coaching
  - Show updated intelligence
```

### Key Backend Endpoints (`live_call.py`)

#### WebSocket Endpoint

**`ws://backend/api/live-call/ws/{call_id}?role={operator|scammer}`**

**Connection Flow:**
1. Frontend connects with `call_id` and `role`
2. Backend creates/retrieves `CallSession` from `CallManager`
3. Registers WebSocket to appropriate role (operator_ws/scammer_ws)
4. Sends connection confirmation
5. Waits for both participants before activating call

**Message Types (Incoming):**
- `{"type": "audio", "data": "base64...", "format": "webm"}` - Audio chunk
- `{"type": "ping"}` - Keep-alive
- `{"type": "end_call"}` - End call request

**Message Types (Outgoing):**
- `{"type": "connected", "role": "operator", "call_id": "..."}` - Connection success
- `{"type": "transcription", "speaker": "operator", "text": "..."}` - Transcription
- `{"type": "audio", "data": "base64...", "from": "operator"}` - Relay audio
- `{"type": "ai_coaching", "text": "...", "audio": "base64...", "strategy": "..."}` - AI coaching (operator only)
- `{"type": "intelligence", "entities": [...], "threat_level": 0.75}` - Intelligence update
- `{"type": "call_ended"}` - Call ended notification

#### REST Endpoints

**`POST /api/live-call/start`** - Create a new call session  
**`POST /api/live-call/end/{call_id}`** - End call and disconnect all  
**`GET /api/live-call/status/{call_id}`** - Get call status

### Audio Processing Pipeline

#### StreamingTranscriber (`features/live_takeover/streaming_stt.py`)

```python
class StreamingTranscriber:
    def __init__(self):
        self.buffer = bytearray()
        self.min_chunk_size = 16000 * 2 * 3  # 3 seconds @ 16kHz mono 16-bit
        self.stt_service = STTService()
    
    def add_chunk(self, audio_bytes: bytes) -> bool:
        """Add audio chunk to buffer. Returns True if ready to transcribe."""
        self.buffer.extend(audio_bytes)
        return len(self.buffer) >= self.min_chunk_size
    
    async def transcribe_buffer(self) -> dict:
        """Transcribe buffered audio and clear buffer."""
        if len(self.buffer) < self.min_chunk_size:
            return None
        
        # Convert buffer to WAV
        audio_data = bytes(self.buffer)
        result = await self.stt_service.transcribe(audio_data, format="pcm")
        
        # Clear buffer after transcription
        self.buffer.clear()
        
        return result
```

#### AudioNormalizer

```python
class AudioNormalizer:
    def normalize_chunk(self, audio_bytes: bytes, format: str = "webm") -> bytes:
        """Normalize audio to 16kHz mono PCM."""
        # Convert webm/mp3 → 16kHz mono PCM
        # Use pydub or ffmpeg
        return normalized_pcm_bytes
```

### WebRTC-Based Live Call (Alternative)

**Files:** `live_call_webrtc.py`, `webrtc_signaling.py`, `LiveCallWebRTC.jsx`

**Architecture:**
- Uses **Socket.IO** for WebRTC signaling
- **Peer-to-peer audio** between operator and scammer
- Backend only handles signaling (offer, answer, ICE candidates)
- TURN server for NAT traversal (configured in `.env`)

**Advantages:**
- Lower server bandwidth (P2P audio)
- Reduced latency

**Disadvantages:**
- Complex signaling logic
- TURN server required for production
- AI coaching requires separate audio tap

**Signaling Flow:**
```
Operator creates offer → Send via Socket.IO
Backend relays offer to Scammer
Scammer creates answer → Send via Socket.IO
Backend relays answer to Operator
ICE candidates exchanged
P2P connection established
Audio flows directly between peers
```

---

## Data Flow & Communication Patterns

### 1. Voice Playground Flow

```
User Recording
  ↓
[Frontend] MediaRecorder captures audio (webm)
  ↓
[Frontend] FormData upload to /api/voice/upload
  ↓
[Backend] Voice API Router (voice.py)
  ↓
[Backend] Voice Adapter processes:
  1. Audio format conversion (audio_processor)
  2. STT transcription (Faster-Whisper)
  3. Agent processing (LangGraph)
  4. TTS synthesis (ElevenLabs)
  5. Cloudinary upload
  ↓
[Backend] Response:
  {
    "transcription": "...",
    "reply": "...",
    "audioUrl": "https://cloudinary.com/.../audio.mp3"
  }
  ↓
[Frontend] Display transcription + play audio via VoicePlayer
```

### 2. Live Takeover (AI Takeover Mode) Flow

```
Scammer speaks
  ↓
[Frontend] MediaRecorder → WebSocket → Backend
  ↓
[Backend] StreamingTranscriber buffers and transcribes
  ↓
[Backend] Intelligence Pipeline:
  - Extract entities
  - Detect tactics
  - Calculate threat
  ↓
[Backend] Takeover Agent (LangGraph):
  - Analyze intent
  - Generate AI response
  ↓
[Backend] TTS (ElevenLabs):
  - Synthesize AI response
  ↓
[Backend] Send AI response to scammer:
  {
    "type": "ai_response",
    "text": "...",
    "audio": "base64...",
    "strategy": "empathy",
    "threat_level": 0.8
  }
  ↓
[Frontend] Play AI response audio to scammer
```

### 3. Live Takeover (AI Coached Mode) Flow

```
Scammer speaks
  ↓
[Backend] Transcribe + Intelligence extraction (same as above)
  ↓
[Backend] Takeover Agent generates coaching scripts:
  [
    "Ask them why they need the bank details",
    "Request their company registration number",
    "Show empathy and build trust"
  ]
  ↓
[Backend] Send coaching to operator:
  {
    "type": "coaching_scripts",
    "scripts": [...],
    "strategy": "information_extraction",
    "threat_level": 0.8
  }
  ↓
[Frontend] Display scripts to operator
  ↓
Operator speaks their own response (NOT AI-generated)
  ↓
Audio relayed to scammer via WebSocket
```

### 4. Session Lifecycle Management

```
Session Creation (POST /api/sessions/create)
  ↓
Status: "active"
Message exchange (text or voice)
  ↓
Intelligence extraction on each message
Scam score calculation
  ↓
Lifecycle manager checks termination conditions:
  - Scam confirmed (score > threshold)
  - Session duration exceeded
  - Manual termination
  ↓
Status: "terminated"
  ↓
Background task:
  - Generate report (JSON/PDF/CSV)
  - Send callback notification (if configured)
  - Archive session data
```

---

## Technology Stack

### Backend Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | FastAPI 0.109+ | Async REST API + WebSocket server |
| **Language** | Python 3.11+ | Backend runtime |
| **AI Agent** | LangGraph | Stateful AI workflow orchestration |
| **LLM Primary** | Groq (Llama 3.3 70B) | Intent analysis, strategy, response generation |
| **LLM Fallback** | Google Gemini 1.5 Flash | Backup LLM when Groq unavailable |
| **TTS Primary** | ElevenLabs API | High-quality voice synthesis |
| **TTS Fallback** | Piper, gTTS, pyttsx3 | Fallback TTS engines |
| **STT** | Faster-Whisper (tiny) | Audio transcription (CPU-optimized) |
| **Database** | MongoDB Atlas | Sessions, messages, intelligence data |
| **Cache/Queue** | Redis | Rate limiting, session cache |
| **Storage** | Cloudinary CDN | Audio file storage (cloud) |
| **Storage Alt** | MinIO / Local FS | Alternative storage backends |
| **WebSocket** | FastAPI WebSockets | Real-time bidirectional communication |
| **WebRTC** | Socket.IO | WebRTC signaling server |
| **Rate Limiting** | SlowAPI | API rate limiting with Redis backend |
| **Auth** | JWT (PyJWT) | Token-based authentication |
| **Audio Processing** | pydub, numpy, soundfile | Audio format conversion & processing |
| **URL Scanning** | VirusTotal API | Malicious URL detection |

### Frontend Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | React 18+ | UI library |
| **Build Tool** | Vite 5+ | Fast dev server & production build |
| **Routing** | React Router v6 | Client-side routing |
| **Styling** | Tailwind CSS 3+ | Utility-first CSS framework |
| **Animations** | Framer Motion | Page transitions & component animations |
| **Icons** | Lucide React | Icon library |
| **Audio** | MediaRecorder API | Browser audio recording |
| **WebSocket** | WebSocket API | Real-time server communication |
| **WebRTC** | WebRTC API | Peer-to-peer audio (alternative) |
| **Mobile** | Capacitor | Native mobile builds (iOS/Android) |
| **PWA** | Service Workers | Progressive Web App capabilities |

### External Services

| Service | Purpose |
|---------|---------|
| **ElevenLabs** | Premium TTS voice synthesis |
| **Cloudinary** | CDN for audio file storage & delivery |
| **MongoDB Atlas** | Managed MongoDB database |
| **Redis Cloud** | Managed Redis cache |
| **VirusTotal** | URL threat scanning |
| **Groq** | LLM API (Llama models) |
| **Google AI** | Gemini LLM API |

---

## Database Schema

### Collections

#### `sessions` Collection

```javascript
{
  "_id": ObjectId("..."),
  "session_id": "uuid-string",
  "start_time": ISODate("2026-02-21T10:00:00Z"),
  "last_updated": ISODate("2026-02-21T10:15:00Z"),
  "status": "active", // active | terminated | reported
  "message_count": 12,
  "scam_score": 0.85,
  "is_confirmed_scam": true,
  
  // Intelligence
  "extracted_intelligence": {
    "bank_accounts": ["1234567890"],
    "upi_ids": ["scammer@upi"],
    "phone_numbers": ["+91-9876543210"],
    "urls": ["https://phishing-site.com"],
    "scam_keywords": ["urgent", "OTP", "bank"],
    "behavioral_tactics": ["urgency", "authority", "fear"]
  },
  
  // Agent Memory
  "agent_state": {
    "turn_count": 12,
    "sentiment": "confused",
    "last_action": "question",
    "notes": "Scammer posing as bank official"
  },
  
  // Voice Fields
  "voice_enabled": true,
  "detected_language": "en",
  "voice_mode": "ai_speaks", // text | ai_speaks | ai_suggests
  "audio_chunk_count": 8,
  "total_audio_duration": 120.5, // seconds
  
  // Metadata
  "client_ip": "192.168.1.100",
  "language": "en"
}
```

#### `messages` Collection

```javascript
{
  "_id": ObjectId("..."),
  "message_id": "uuid-string",
  "session_id": "uuid-string", // Foreign key to sessions
  "sender": "scammer", // scammer | agent
  "content": "Please share your bank OTP",
  "timestamp": ISODate("2026-02-21T10:05:00Z"),
  
  // Voice Fields
  "is_voice": true,
  "audio_file_path": "https://res.cloudinary.com/.../audio.mp3",
  "transcription_confidence": 0.95,
  "speech_naturalized": false, // true for agent responses
  
  // Metadata
  "metadata": {
    "confidence": 0.95,
    "language": "en",
    "duration": 5.2 // seconds
  }
}
```

#### `voice_chunks` Collection (Optional)

```javascript
{
  "_id": ObjectId("..."),
  "chunk_id": "uuid-string",
  "session_id": "uuid-string",
  "file_path": "/storage/audio/chunk_001.wav",
  "format": "wav",
  "sample_rate": 16000,
  "duration": 3.0, // seconds
  "sequence_number": 1,
  "timestamp": ISODate("2026-02-21T10:05:00Z"),
  "processed": true,
  "transcription": "Hello, is this the bank?",
  "transcription_confidence": 0.92
}
```

### Indexes

```javascript
// sessions collection
db.sessions.createIndex({ "session_id": 1 }, { unique: true })
db.sessions.createIndex({ "status": 1 })
db.sessions.createIndex({ "is_confirmed_scam": 1 })
db.sessions.createIndex({ "start_time": -1 })

// messages collection
db.messages.createIndex({ "session_id": 1, "timestamp": 1 })
db.messages.createIndex({ "message_id": 1 }, { unique: true })
db.messages.createIndex({ "sender": 1 })
db.messages.createIndex({ "is_voice": 1 })

// voice_chunks collection
db.voice_chunks.createIndex({ "session_id": 1, "sequence_number": 1 })
db.voice_chunks.createIndex({ "processed": 1 })
```

---

## Security & Authentication

### Authentication Methods

#### 1. **API Key Authentication**
- Used for backend API access
- Key stored in `config.py`: `API_SECRET_KEY`
- Header: `X-API-Key: {key}`
- Validated via `core/auth.py::verify_api_key()`

#### 2. **JWT Token Authentication**
- Used for user sessions (future)
- Access token expires in 30 minutes
- Refresh token expires in 7 days
- Tokens signed with `JWT_SECRET_KEY`
- Algorithm: HS256

### Security Features

#### Rate Limiting
- Implemented via **SlowAPI**
- Redis-backed distributed rate limiting
- Default: 200 requests/minute per IP
- Voice upload: 30 requests/minute per IP

#### CORS Configuration
- Configurable allowed origins via `CORS_ORIGINS` env var
- Supports multiple domains (comma-separated)
- Credentials allowed for authenticated requests

#### Input Validation
- Pydantic models for request/response validation
- Audio file format validation (wav, mp3, webm)
- File size limits (10MB for audio uploads)

#### Data Protection
- MongoDB connection via secure URI (TLS)
- API keys stored in environment variables (never in code)
- Cloudinary URLs signed (optional)
- Audio files auto-expire (configurable TTL)

---

## Deployment Architecture

### Production Deployment Options

#### Option 1: Docker Compose (Recommended for Development)

```yaml
version: '3.8'

services:
  backend:
    build: ./honeypot/backend
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URI=${MONGODB_URI}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
    depends_on:
      - mongo
      - redis

  frontend:
    build: ./honeypot/frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  mongo_data:
```

#### Option 2: Cloud Deployment (Render.com)

**Backend Service:**
- Type: Web Service
- Build Command: `cd honeypot/backend && pip install -r requirements.txt`
- Start Command: `cd honeypot/backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment: Python 3.11
- Instance: Standard

**Frontend Service:**
- Type: Static Site
- Build Command: `cd honeypot/frontend && npm install && npm run build`
- Publish Directory: `honeypot/frontend/dist`

**Environment Variables:**
- MongoDB Atlas URI (cloud database)
- External Redis (RedisLabs/Upstash)
- Cloudinary credentials (cloud storage)

### Environment Configuration

**Backend `.env`:**
```env
# Core
API_SECRET_KEY=your-secret-key
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Database
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=honeycatcher

# LLM
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...

# Voice
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Storage
CLOUDINARY_CLOUD_NAME=your-cloud
CLOUDINARY_API_KEY=123...
CLOUDINARY_API_SECRET=abc...

# Security
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256

# Rate Limiting
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=http://localhost:5173,https://yourdomain.com
```

**Frontend `.env`:**
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
VITE_TURN_URL=turn:localhost:3478
VITE_TURN_USERNAME=honeybadger
VITE_TURN_CREDENTIAL=your-turn-password
```

### Scaling Considerations

#### Horizontal Scaling
- **Backend**: Deploy multiple FastAPI instances behind load balancer
- **WebSocket**: Use Redis Pub/Sub for WebSocket session sharing across instances
- **Database**: MongoDB Atlas with replica sets
- **Cache**: Redis Cluster for distributed caching

#### Vertical Scaling
- **STT Processing**: GPU instances for Faster-Whisper acceleration
- **TTS Processing**: Dedicated instances for ElevenLabs API calls
- **Storage**: Increase Cloudinary plan for large audio volumes

#### Performance Optimizations
- **CDN**: Use Cloudinary CDN for audio delivery
- **Caching**: Cache agent responses for common queries
- **Async Processing**: Background tasks for intelligence extraction
- **Connection Pooling**: MongoDB connection pool (max 100 connections)

---

## Appendix: Key Workflows

### Workflow 1: Session Initialization

```
POST /api/sessions/create
  ↓
Generate UUID session_id
  ↓
Create Session document in MongoDB
  - status: "active"
  - start_time: now()
  - agent_state: initial state
  ↓
Return session_id to frontend
  ↓
Frontend stores session in state
```

### Workflow 2: Voice Message Processing

```
Frontend: Record audio (MediaRecorder)
  ↓
FormData upload: /api/voice/upload
  - audio: Blob (webm)
  - sessionId: string
  - mode: "ai_speaks" | "ai_suggests"
  ↓
Backend: voice_adapter.run_voice_turn()
  1. Convert audio format
  2. STT transcribe (Faster-Whisper)
  3. Fetch session history
  4. Agent processing (LangGraph)
  5. Speech naturalization
  6. TTS synthesis (ElevenLabs)
  7. Upload to Cloudinary
  8. Save messages to MongoDB
  ↓
Return response:
  {
    "transcription": "...",
    "reply": "...",
    "audioUrl": "https://cloudinary..."
  }
  ↓
Frontend: Display + play audio
```

### Workflow 3: Live Call Connection

```
Frontend: Navigate to /live-call?call_id=123&role=operator
  ↓
Connect WebSocket: ws://backend/api/live-call/ws/123?role=operator
  ↓
Backend: CallManager.connect_operator(123, ws)
  - Create CallSession if not exists
  - Register operator WebSocket
  - Send {"type": "connected"}
  ↓
Frontend: Display "Waiting for scammer..."
  ↓
Scammer connects (same call_id, role=scammer)
  ↓
Backend: CallSession.has_both_participants() == True
  ↓
Send to both: {"type": "participant_joined"}
  ↓
Call active - audio routing enabled
```

### Workflow 4: AI Coaching Generation

```
Scammer audio received via WebSocket
  ↓
Transcribe scammer audio
  ↓
Parallel execution:
  1. Intelligence Pipeline:
     - Extract entities (regex + LLM)
     - Detect tactics (pattern matching)
     - Calculate threat level
     - Update session in MongoDB
  
  2. Takeover Agent (if operator role):
     - Analyze scammer intent
     - Generate coaching suggestions
     - Select strategy
     - TTS synthesize coaching
  ↓
Send to operator WebSocket:
{
  "type": "ai_coaching",
  "text": "Ask for their callback number",
  "audio": "base64_audio_data",
  "strategy": "information_extraction",
  "entities": [...],
  "threat_level": 0.8,
  "tactics": ["urgency", "authority"]
}
  ↓
Operator receives coaching in UI
  - Audio plays automatically
  - Text displayed in coaching panel
  - Intelligence updated in dashboard
```

---

## Summary

**HoneyBadger** is a full-stack AI-powered honeypot system with:

- **Layered architecture**: Frontend, API Gateway, Business Logic, Services, Data
- **Real-time capabilities**: WebSocket-based live calls with bidirectional audio
- **AI-driven engagement**: LangGraph agent with intent analysis and strategy planning
- **Voice processing**: ElevenLabs TTS + Faster-Whisper STT
- **Intelligence extraction**: Real-time entity and tactic detection
- **Scalable design**: Microservices-ready with Redis caching and MongoDB clustering
- **Security-first**: JWT auth, rate limiting, input validation, CORS protection

The **Live Call** feature is the crown jewel, enabling real-time operator-scammer voice communication with AI coaching, making it a powerful tool for scam research and evidence collection.

---

**Document Version:** 1.0  
**Last Updated:** February 21, 2026  
**Maintainer:** HoneyBadger Development Team
