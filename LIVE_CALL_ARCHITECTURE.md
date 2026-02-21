# Live Call Architecture - Deep Dive

> **Detailed Technical Architecture for Live Call Feature**  
> HoneyBadger Real-Time Voice Communication System

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Component Breakdown](#component-breakdown)
4. [Audio Pipeline](#audio-pipeline)
5. [WebSocket Protocol](#websocket-protocol)
6. [State Management](#state-management)
7. [AI Coaching Pipeline](#ai-coaching-pipeline)
8. [Error Handling & Recovery](#error-handling--recovery)
9. [Performance Optimization](#performance-optimization)
10. [Mobile Optimization](#mobile-optimization)

---

## Overview

The **Live Call** feature enables real-time, two-way voice communication between an **operator** (honeypot controller) and a **scammer**, with AI-powered intelligence extraction and coaching in real-time.

### Key Features

✅ **Real-time bidirectional audio streaming**  
✅ **Live transcription** for both participants  
✅ **AI coaching** for the operator with synthesized voice suggestions  
✅ **Intelligence extraction** (entities, tactics, threat scoring)  
✅ **Audio recording** with Cloudinary storage  
✅ **Mobile-optimized UI** with PWA support  
✅ **Low-latency communication** (<500ms audio relay)

### Two Implementation Approaches

1. **WebSocket-Based** (Current Production) - Server-mediated audio relay
2. **WebRTC P2P** (Alternative) - Peer-to-peer with signaling server

---

## Architecture Diagram

### System-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌──────────────────────────────┐   ┌──────────────────────────┐  │
│   │    OPERATOR FRONTEND         │   │   SCAMMER FRONTEND       │  │
│   │    (LiveCall.jsx)            │   │   (LiveCall.jsx)         │  │
│   │                              │   │                          │  │
│   │  ┌────────────────────────┐ │   │  ┌────────────────────┐ │  │
│   │  │  MediaRecorder API     │ │   │  │  MediaRecorder API │ │  │
│   │  │  - Capture Mic Audio   │ │   │  │  - Capture Audio   │ │  │
│   │  │  - Format: audio/webm  │ │   │  │  - Format: webm    │ │  │
│   │  └────────────────────────┘ │   │  └────────────────────┘ │  │
│   │           ↓                  │   │           ↓              │  │
│   │  ┌────────────────────────┐ │   │  ┌────────────────────┐ │  │
│   │  │  Base64 Encode         │ │   │  │  Base64 Encode     │ │  │
│   │  └────────────────────────┘ │   │  └────────────────────┘ │  │
│   │           ↓                  │   │           ↓              │  │
│   │  ┌────────────────────────┐ │   │  ┌────────────────────┐ │  │
│   │  │  WebSocket Send        │ │   │  │  WebSocket Send    │ │  │
│   │  │  {type: "audio"}       │ │   │  │  {type: "audio"}   │ │  │
│   │  └────────────────────────┘ │   │  └────────────────────┘ │  │
│   │           ↓                  │   │           ↓              │  │
│   │           └──────────────────┼───┼──────────┘              │  │
│   │                              │   │                          │  │
│   │  ┌────────────────────────┐ │   │  ┌────────────────────┐ │  │
│   │  │  Web Audio API         │ │   │  │  Web Audio API     │ │  │
│   │  │  - Decode & Play       │ │   │  │  - Decode & Play   │ │  │
│   │  └────────────────────────┘ │   │  └────────────────────┘ │  │
│   │           ↑                  │   │           ↑              │  │
│   │  ┌────────────────────────┐ │   │  ┌────────────────────┐ │  │
│   │  │  WebSocket Receive     │ │   │  │  WebSocket Receive │ │  │
│   │  │  {type: "audio"}       │ │   │  │  {type: "audio"}   │ │  │
│   │  └────────────────────────┘ │   │  └────────────────────┘ │  │
│   │                              │   │                          │  │
│   │  ┌────────────────────────┐ │   │                          │  │
│   │  │  AI Coaching Display   │ │   │                          │  │
│   │  │  - Text Suggestions    │ │   │   (No AI Coaching)       │  │
│   │  │  - Audio Playback      │ │   │                          │  │
│   │  │  - Intelligence Panel  │ │   │                          │  │
│   │  └────────────────────────┘ │   │                          │  │
│   └──────────────────────────────┘   └──────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
                                 ↕ WebSocket
┌─────────────────────────────────────────────────────────────────────┐
│                        SERVER LAYER                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │              CallManager (Session Orchestration)             │  │
│   │                                                               │  │
│   │  ┌──────────────────────────────────────────────────────┐   │  │
│   │  │           CallSession (In-Memory State)              │   │  │
│   │  │                                                       │   │  │
│   │  │  call_id: "abc-123"                                  │   │  │
│   │  │  operator_ws: WebSocket                              │   │  │
│   │  │  scammer_ws: WebSocket                               │   │  │
│   │  │  operator_transcriber: StreamingTranscriber          │   │  │
│   │  │  scammer_transcriber: StreamingTranscriber           │   │  │
│   │  │  normalizer: AudioNormalizer                         │   │  │
│   │  │  transcript: [...]                                   │   │  │
│   │  │  entities: [...]                                     │   │  │
│   │  │  threat_level: 0.75                                  │   │  │
│   │  │  tactics: ["urgency", "authority"]                   │   │  │
│   │  │                                                       │   │  │
│   │  └──────────────────────────────────────────────────────┘   │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                 ↓                                    │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                   Audio Processing Pipeline                  │  │
│   │                                                               │  │
│   │  Receive → Decode → Normalize → Buffer → Transcribe → Relay │  │
│   │                                                               │  │
│   │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │  │
│   │  │ Audio        │   │ Audio        │   │ Streaming    │    │  │
│   │  │ Normalizer   │→  │ Buffer       │→  │ Transcriber  │    │  │
│   │  │ (16kHz mono) │   │ (3s chunks)  │   │ (Whisper)    │    │  │
│   │  └──────────────┘   └──────────────┘   └──────────────┘    │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                 ↓                                    │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                  AI Processing Pipeline                      │  │
│   │                    (Operator Only)                           │  │
│   │                                                               │  │
│   │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │  │
│   │  │ Intelligence │   │ Takeover     │   │ ElevenLabs   │    │  │
│   │  │ Extractor    │→  │ Agent        │→  │ TTS          │    │  │
│   │  │ (Entities)   │   │ (LangGraph)  │   │ (Coaching)   │    │  │
│   │  └──────────────┘   └──────────────┘   └──────────────┘    │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
                                 ↕
┌─────────────────────────────────────────────────────────────────────┐
│                      SERVICES & DATA LAYER                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│   │ Faster       │  │ ElevenLabs   │  │ Cloudinary   │             │
│   │ Whisper STT  │  │ TTS API      │  │ Audio Store  │             │
│   └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                       │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│   │ MongoDB      │  │ Redis        │  │ VirusTotal   │             │
│   │ (Sessions)   │  │ (Cache)      │  │ (URL Scan)   │             │
│   └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Frontend Components

#### LiveCall.jsx (Main Component)

**Location:** `honeypot/frontend/src/pages/LiveCall.jsx`

**Responsibilities:**
- WebSocket connection management
- Audio recording via MediaRecorder
- Audio playback via Web Audio API
- Real-time UI updates (transcript, coaching, intelligence)
- Call lifecycle management (connect, active, end)

**State Management:**
```javascript
{
  isConnected: boolean,              // WebSocket connection status
  status: string,                    // "Connecting", "Active", "Ended"
  transcript: Array<TranscriptItem>, // [{speaker, text, timestamp}]
  aiCoaching: Array<CoachingItem>,   // [{text, audio, strategy}]
  entities: Array<Entity>,           // [{type, value, timestamp}]
  threatLevel: number,               // 0-1 scale
  tactics: Array<string>,            // ["urgency", "authority", ...]
  isRecording: boolean,              // Mic recording state
  participantConnected: boolean      // Both operator & scammer connected
}
```

**Key Methods:**
```javascript
// WebSocket Management
const connectWebSocket = () => {
  const role = searchParams.get('role'); // operator | scammer
  const wsUrl = `${WS_BASE}/api/live-call/ws/${callId}?role=${role}`;
  wsRef.current = new WebSocket(wsUrl);
  
  wsRef.current.onopen = handleOpen;
  wsRef.current.onmessage = handleMessage;
  wsRef.current.onerror = handleError;
  wsRef.current.onclose = handleClose;
};

// Audio Recording
const startRecording = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
  
  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) {
      sendAudioChunk(e.data);
    }
  };
  
  mediaRecorder.start(250); // 250ms chunks
};

// Audio Transmission
const sendAudioChunk = async (audioBlob) => {
  const reader = new FileReader();
  reader.onloadend = () => {
    const base64 = reader.result.split(',')[1];
    wsRef.current.send(JSON.stringify({
      type: 'audio',
      data: base64,
      format: 'webm'
    }));
  };
  reader.readAsDataURL(audioBlob);
};

// Audio Playback
const playAudio = async (base64Audio) => {
  const audioContext = audioContextRef.current || new AudioContext();
  const audioData = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0));
  const audioBuffer = await audioContext.decodeAudioData(audioData.buffer);
  
  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  source.start(0);
};
```

#### MobileOptimizedLiveCall.jsx

**Location:** `honeypot/frontend/src/components/MobileOptimizedLiveCall.jsx`

**Mobile Optimizations:**
- Touch-optimized controls (larger buttons)
- Reduced audio chunk size (100ms vs 250ms)
- Audio context unlocking on user interaction
- Scroll-optimized transcript view
- Battery-saving mode (reduce transcription frequency)

### 2. Backend Components

#### CallManager (Session Orchestrator)

**Location:** `honeypot/backend/api/live_call.py`

**Class Definition:**
```python
class CallManager:
    """Manages active call sessions and audio routing."""
    
    def __init__(self):
        self.sessions: Dict[str, CallSession] = {}
        self.operator_to_call: Dict[WebSocket, str] = {}
        self.scammer_to_call: Dict[WebSocket, str] = {}
    
    def create_session(self, call_id: str) -> CallSession:
        """Create a new call session."""
        session = CallSession(call_id)
        self.sessions[call_id] = session
        return session
    
    async def connect_operator(self, call_id: str, ws: WebSocket) -> CallSession:
        """Connect operator to call session."""
        session = self.sessions.get(call_id)
        if not session:
            session = self.create_session(call_id)
        
        await ws.accept()
        session.operator_ws = ws
        self.operator_to_call[ws] = call_id
        
        await self.send_to_operator(call_id, {
            "type": "connected",
            "role": "operator",
            "call_id": call_id
        })
        
        return session
    
    async def connect_scammer(self, call_id: str, ws: WebSocket) -> CallSession:
        """Connect scammer to call session."""
        # Similar to connect_operator but for scammer role
        pass
    
    async def relay_audio(
        self, 
        call_id: str, 
        from_role: str, 
        audio_data: bytes
    ):
        """Relay audio from one participant to the other."""
        session = self.sessions.get(call_id)
        if not session or not session.has_both_participants():
            return
        
        # Encode audio
        audio_b64 = base64.b64encode(audio_data).decode()
        
        # Send to opposite participant
        target_ws = (
            session.scammer_ws if from_role == "operator" 
            else session.operator_ws
        )
        
        await target_ws.send_json({
            "type": "audio",
            "data": audio_b64,
            "from": from_role,
            "timestamp": datetime.utcnow().isoformat()
        })
```

#### CallSession (State Container)

**Class Definition:**
```python
class CallSession:
    """Represents an active two-way call session."""
    
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.operator_ws: Optional[WebSocket] = None
        self.scammer_ws: Optional[WebSocket] = None
        
        # Audio Processing
        self.operator_transcriber = StreamingTranscriber()
        self.scammer_transcriber = StreamingTranscriber()
        self.normalizer = AudioNormalizer()
        
        # Session State
        self.transcript = []  # [{speaker, text, timestamp}]
        self.entities = []    # [{type, value, confidence}]
        self.threat_level = 0.0
        self.tactics = []
        self.start_time = datetime.utcnow()
        self.is_active = True
        
        # Audio Recording (optional)
        self.recorded_audio = []  # [bytes] for evidence
    
    def has_both_participants(self) -> bool:
        """Check if both operator and scammer are connected."""
        return self.operator_ws is not None and self.scammer_ws is not None
    
    async def close_all(self):
        """Close all connections gracefully."""
        self.is_active = False
        if self.operator_ws:
            try:
                await self.operator_ws.close()
            except:
                pass
        if self.scammer_ws:
            try:
                await self.scammer_ws.close()
            except:
                pass
```

---

## Audio Pipeline

### Step-by-Step Audio Flow

#### Operator Speaks → Scammer Hears

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Capture (Frontend - Operator)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  navigator.mediaDevices.getUserMedia({ audio: true })            │
│          ↓                                                        │
│  MediaRecorder(stream, { mimeType: 'audio/webm' })               │
│          ↓                                                        │
│  ondataavailable → audioBlob (every 250ms)                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Encode & Send (Frontend - Operator)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  FileReader.readAsDataURL(audioBlob)                             │
│          ↓                                                        │
│  base64String = result.split(',')[1]                             │
│          ↓                                                        │
│  WebSocket.send(JSON.stringify({                                 │
│    type: 'audio',                                                │
│    data: base64String,                                           │
│    format: 'webm'                                                │
│  }))                                                             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                               ↓ WebSocket
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Receive & Decode (Backend)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  message = await websocket.receive_json()                        │
│  audio_b64 = message['data']                                     │
│          ↓                                                        │
│  audio_bytes = base64.b64decode(audio_b64)                       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Normalize Audio (Backend - AudioNormalizer)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  def normalize_chunk(audio_bytes, format='webm'):                │
│    # Convert to 16kHz mono PCM                                   │
│    audio = AudioSegment.from_file(                               │
│      io.BytesIO(audio_bytes), format='webm'                      │
│    )                                                             │
│    audio = audio.set_frame_rate(16000).set_channels(1)          │
│    return audio.raw_data                                         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Buffer & Transcribe (Backend - StreamingTranscriber)    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  transcriber.add_chunk(normalized_audio)                         │
│          ↓                                                        │
│  if buffer >= 3 seconds:                                         │
│    result = await stt_service.transcribe(buffer)                 │
│    transcription = result['text']                                │
│    buffer.clear()                                                │
│          ↓                                                        │
│  Send transcription to BOTH participants:                        │
│    {                                                             │
│      type: 'transcription',                                      │
│      speaker: 'operator',                                        │
│      text: transcription,                                        │
│      language: 'en',                                             │
│      confidence: 0.95                                            │
│    }                                                             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Relay Audio (Backend - CallManager)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  relay_audio(call_id, from_role='operator', audio_bytes)         │
│          ↓                                                        │
│  target_ws = session.scammer_ws                                  │
│  audio_b64 = base64.b64encode(audio_bytes).decode()             │
│          ↓                                                        │
│  await target_ws.send_json({                                     │
│    type: 'audio',                                                │
│    data: audio_b64,                                              │
│    from: 'operator'                                              │
│  })                                                              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                               ↓ WebSocket
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: Playback (Frontend - Scammer)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  wsRef.onmessage = (event) => {                                  │
│    const msg = JSON.parse(event.data);                           │
│    if (msg.type === 'audio') {                                   │
│      playAudio(msg.data);                                        │
│    }                                                             │
│  }                                                               │
│                                                                   │
│  const playAudio = async (base64Audio) => {                      │
│    const audioContext = new AudioContext();                      │
│    const audioData = Uint8Array.from(                            │
│      atob(base64Audio), c => c.charCodeAt(0)                     │
│    );                                                            │
│    const audioBuffer = await audioContext.decodeAudioData(       │
│      audioData.buffer                                            │
│    );                                                            │
│                                                                   │
│    const source = audioContext.createBufferSource();             │
│    source.buffer = audioBuffer;                                  │
│    source.connect(audioContext.destination);                     │
│    source.start(0);                                              │
│  };                                                              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Total Latency Breakdown:**
- Audio capture: ~250ms (chunk size)
- Base64 encoding: ~10ms
- WebSocket transmission: ~50-100ms (network)
- Backend processing: ~50ms (decode + normalize)
- Transcription: ~300ms (Faster-Whisper tiny model)
- Audio relay: ~50ms
- Frontend playback: ~20ms

**Total End-to-End: ~400-500ms** (acceptable for voice communication)

---

## WebSocket Protocol

### Connection Endpoint

```
ws://backend/api/live-call/ws/{call_id}?role={operator|scammer}
```

**Parameters:**
- `call_id`: Unique call session identifier (UUID)
- `role`: Participant role (`operator` or `scammer`)

### Message Types

#### Client → Server

**1. Audio Chunk**
```json
{
  "type": "audio",
  "data": "base64_encoded_audio_data",
  "format": "webm",
  "timestamp": "2026-02-21T10:05:30.123Z"
}
```

**2. End Call**
```json
{
  "type": "end_call"
}
```

**3. Ping (Keep-Alive)**
```json
{
  "type": "ping"
}
```

#### Server → Client

**1. Connection Confirmation**
```json
{
  "type": "connected",
  "role": "operator",
  "call_id": "abc-123-xyz",
  "timestamp": "2026-02-21T10:00:00.000Z"
}
```

**2. Participant Joined**
```json
{
  "type": "participant_joined",
  "role": "scammer",
  "message": "Scammer has joined the call"
}
```

**3. Audio Relay**
```json
{
  "type": "audio",
  "data": "base64_encoded_audio_data",
  "from": "operator",
  "timestamp": "2026-02-21T10:05:30.456Z"
}
```

**4. Transcription**
```json
{
  "type": "transcription",
  "speaker": "operator",
  "text": "Hello, this is customer service",
  "language": "en",
  "confidence": 0.95,
  "timestamp": "2026-02-21T10:05:33.000Z"
}
```

**5. AI Coaching (Operator Only)**
```json
{
  "type": "ai_coaching",
  "text": "Ask for their callback number to verify",
  "audio": "base64_encoded_tts_audio",
  "strategy": "information_extraction",
  "intent": "verify_identity",
  "threat_level": 0.75,
  "timestamp": "2026-02-21T10:05:35.000Z"
}
```

**6. Intelligence Update**
```json
{
  "type": "intelligence",
  "entities": [
    {"type": "phone", "value": "+91-9876543210", "confidence": 0.9},
    {"type": "url", "value": "https://phishing-site.com", "confidence": 1.0}
  ],
  "threat_level": 0.8,
  "tactics": ["urgency", "authority", "fear"],
  "timestamp": "2026-02-21T10:05:36.000Z"
}
```

**7. Call Ended**
```json
{
  "type": "call_ended",
  "reason": "user_disconnect",
  "duration_seconds": 300,
  "timestamp": "2026-02-21T10:10:00.000Z"
}
```

**8. Error**
```json
{
  "type": "error",
  "message": "Transcription service unavailable",
  "code": "STT_ERROR",
  "timestamp": "2026-02-21T10:05:40.000Z"
}
```

**9. Pong (Keep-Alive Response)**
```json
{
  "type": "pong"
}
```

---

## State Management

### Backend State (In-Memory)

```python
# Global CallManager instance
call_manager = CallManager()

# CallManager State
{
  "sessions": {
    "call-abc-123": CallSession {
      call_id: "call-abc-123",
      operator_ws: WebSocket<connected>,
      scammer_ws: WebSocket<connected>,
      operator_transcriber: StreamingTranscriber(...),
      scammer_transcriber: StreamingTranscriber(...),
      normalizer: AudioNormalizer(...),
      transcript: [
        {"speaker": "operator", "text": "Hello", "timestamp": "..."},
        {"speaker": "scammer", "text": "Hi", "timestamp": "..."}
      ],
      entities: [
        {"type": "phone", "value": "+91-xxx", "confidence": 0.9}
      ],
      threat_level: 0.75,
      tactics: ["urgency", "authority"],
      start_time: datetime(...),
      is_active: True
    }
  },
  "operator_to_call": {
    WebSocket<operator>: "call-abc-123"
  },
  "scammer_to_call": {
    WebSocket<scammer>: "call-abc-123"
  }
}
```

### Frontend State (React)

```javascript
// LiveCall.jsx state
{
  // Connection
  isConnected: false → true,
  status: "Connecting" → "Active" → "Ended",
  participantConnected: false → true,
  
  // Audio
  isRecording: false → true,
  audioQueue: [],  // [{data: base64, from: role}]
  isPlayingAudio: false,
  
  // Transcript
  transcript: [
    {speaker: "operator", text: "Hello", timestamp: "..."},
    {speaker: "scammer", text: "Hi", timestamp: "..."}
  ],
  
  // AI Coaching (operator only)
  aiCoaching: [
    {
      text: "Ask for their callback number",
      audio: "base64...",
      strategy: "info_extraction",
      timestamp: "..."
    }
  ],
  
  // Intelligence
  entities: [
    {type: "phone", value: "+91-xxx", confidence: 0.9}
  ],
  threatLevel: 0.75,
  tactics: ["urgency", "authority"],
  
  // References
  wsRef: WebSocket,
  mediaRecorderRef: MediaRecorder,
  audioContextRef: AudioContext
}
```

---

## AI Coaching Pipeline

### Detailed Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Scammer Audio Received                                  │
├─────────────────────────────────────────────────────────────────┤
│  WebSocket receives scammer audio chunk                          │
│  → Normalized to 16kHz mono PCM                                  │
│  → Buffered in StreamingTranscriber                              │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Transcription                                            │
├─────────────────────────────────────────────────────────────────┤
│  Faster-Whisper STT (tiny model)                                 │
│  → Input: 3 seconds of buffered audio                            │
│  → Output: {                                                     │
│      text: "Please share your bank OTP now",                     │
│      language: "en",                                             │
│      confidence: 0.95                                            │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Parallel Processing                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────┐   ┌─────────────────────────┐     │
│  │ Intelligence Pipeline    │   │ Takeover Agent         │     │
│  │ (intelligence_pipeline)  │   │ (takeover_agent)       │     │
│  │                          │   │                        │     │
│  │ 1. Extract Entities      │   │ 1. Analyze Intent      │     │
│  │    - Regex patterns      │   │    - LLM analysis      │     │
│  │    - LLM verification    │   │    - Scammer motive    │     │
│  │                          │   │                        │     │
│  │ 2. Detect Tactics        │   │ 2. Generate Strategy   │     │
│  │    - Urgency keywords    │   │    - empathy           │     │
│  │    - Authority claims    │   │    - delay             │     │
│  │    - Fear tactics        │   │    - info_extract      │     │
│  │                          │   │                        │     │
│  │ 3. Calculate Threat      │   │ 3. Create Coaching     │     │
│  │    - Score 0-1           │   │    - Text suggestions  │     │
│  │    - Risk assessment     │   │    - Action prompts    │     │
│  └─────────────────────────┘   └─────────────────────────┘     │
│           ↓                              ↓                       │
│  {                             {                                 │
│    entities: [...],              coaching_text: "...",           │
│    threat_level: 0.8,            strategy: "empathy",            │
│    tactics: [...]                intent: "credential_theft"      │
│  }                             }                                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: TTS Synthesis (ElevenLabs)                              │
├─────────────────────────────────────────────────────────────────┤
│  tts_service.synthesize_to_bytes(                                │
│    text=coaching_text,                                           │
│    voice_id=settings.ELEVENLABS_VOICE_ID                         │
│  )                                                               │
│  → Returns: bytes (mp3 audio)                                    │
│  → Encode to base64 for WebSocket transmission                   │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Send to Operator                                         │
├─────────────────────────────────────────────────────────────────┤
│  await operator_ws.send_json({                                   │
│    "type": "ai_coaching",                                        │
│    "text": "Ask them why they need the OTP urgently",            │
│    "audio": base64_audio,                                        │
│    "strategy": "delay",                                          │
│    "intent": "credential_theft",                                 │
│    "threat_level": 0.8,                                          │
│    "entities": [...],                                            │
│    "tactics": ["urgency", "authority"]                           │
│  })                                                              │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Display & Play (Frontend - Operator)                    │
├─────────────────────────────────────────────────────────────────┤
│  1. Display coaching text in UI panel                            │
│  2. Play audio coaching via Web Audio API                        │
│  3. Update intelligence dashboard (entities, threat, tactics)    │
│  4. Highlight urgent actions in UI                               │
└─────────────────────────────────────────────────────────────────┘
```

### LangGraph Takeover Agent Flow

```python
# Simplified Takeover Agent (features/live_takeover/takeover_agent.py)

async def run(
    scammer_text: str,
    history: List[Dict],
    mode: str = "ai_coached",
    language: str = "en",
    turn_count: int = 0
) -> Dict:
    """
    Process scammer input and generate coaching/response.
    
    Returns:
        {
            "intent": str,              # Scammer's intent
            "strategy": str,            # Recommended strategy
            "coaching_text": str,       # Coaching for operator
            "extracted_data": Dict,     # Entities from this turn
            "scripts": List[str]        # Script suggestions (coached mode)
        }
    """
    
    # 1. Analyze Intent
    intent_result = await llm.ainvoke(
        INTENT_ANALYSIS_PROMPT.format(
            scammer_text=scammer_text,
            history=history
        )
    )
    
    # 2. Plan Strategy
    strategy_result = await llm.ainvoke(
        STRATEGY_PROMPT.format(
            intent=intent_result['intent'],
            scammer_text=scammer_text,
            turn_count=turn_count
        )
    )
    
    # 3. Generate Coaching
    if mode == "ai_coached":
        coaching = await llm.ainvoke(
            COACHING_PROMPT.format(
                intent=intent_result['intent'],
                strategy=strategy_result['strategy'],
                scammer_text=scammer_text
            )
        )
        return {
            "intent": intent_result['intent'],
            "strategy": strategy_result['strategy'],
            "coaching_text": coaching['text'],
            "scripts": coaching['suggestions']
        }
    
    elif mode == "ai_takeover":
        response = await llm.ainvoke(
            RESPONSE_PROMPT.format(
                intent=intent_result['intent'],
                strategy=strategy_result['strategy'],
                scammer_text=scammer_text,
                history=history
            )
        )
        return {
            "intent": intent_result['intent'],
            "strategy": strategy_result['strategy'],
            "response": response['text']
        }
```

---

## Error Handling & Recovery

### Connection Errors

**WebSocket Disconnection:**
```javascript
// Frontend: Auto-reconnect with exponential backoff
const reconnect = () => {
  setTimeout(() => {
    attemptCount++;
    const delay = Math.min(1000 * Math.pow(2, attemptCount), 30000);
    connectWebSocket();
  }, delay);
};

wsRef.current.onclose = (event) => {
  if (event.code !== 1000) {  // Not normal closure
    reconnect();
  }
};
```

**Backend Session Recovery:**
```python
# If WebSocket disconnects, keep session alive for 60 seconds
async def handle_disconnect(call_id: str, role: str):
    session = call_manager.get_session(call_id)
    if session:
        # Wait 60 seconds for reconnection
        await asyncio.sleep(60)
        
        # Check if reconnected
        if role == "operator" and session.operator_ws is None:
            # End session
            await call_manager.end_session(call_id)
```

### Audio Processing Errors

**Transcription Failure:**
```python
try:
    transcription = await transcriber.transcribe_buffer()
except Exception as e:
    logger.error(f"Transcription error: {e}")
    # Send error to client
    await websocket.send_json({
        "type": "error",
        "message": "Transcription temporarily unavailable",
        "code": "STT_ERROR"
    })
    # Continue audio relay without transcription
```

**TTS Failure (AI Coaching):**
```python
try:
    audio_bytes = await elevenlabs_service.synthesize(coaching_text)
except Exception as e:
    logger.warning(f"TTS failed: {e}")
    # Send text-only coaching
    await operator_ws.send_json({
        "type": "ai_coaching",
        "text": coaching_text,
        "audio": None,  # No audio available
        "strategy": strategy
    })
```

### Frontend Error Handling

**Audio Playback Failure:**
```javascript
const playAudio = async (base64Audio) => {
  try {
    const audioContext = new AudioContext();
    const audioData = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0));
    const audioBuffer = await audioContext.decodeAudioData(audioData.buffer);
    
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start(0);
  } catch (error) {
    console.error('Audio playback error:', error);
    // Fallback: Add to queue for retry
    audioQueueRef.current.push({ data: base64Audio, retryCount: 0 });
  }
};
```

---

## Performance Optimization

### Backend Optimizations

**1. Async Processing**
```python
# Process intelligence extraction in parallel with agent response
async def _handle_audio_chunk(...):
    transcription = await transcribe(audio)
    
    # Parallel execution
    intelligence_task = asyncio.create_task(
        intelligence_pipeline.process(transcription)
    )
    agent_task = asyncio.create_task(
        takeover_agent.run(transcription, history)
    )
    
    # Wait for both
    intel_result, agent_result = await asyncio.gather(
        intelligence_task, agent_task
    )
```

**2. Buffer Management**
```python
# Adaptive buffering based on network conditions
class StreamingTranscriber:
    def __init__(self):
        self.min_chunk_size = 16000 * 2 * 3  # 3 seconds default
        self.adaptive_buffer = True
    
    def adjust_buffer_size(self, latency_ms: int):
        """Adjust buffer based on network latency."""
        if latency_ms > 500:
            # High latency: increase buffer to reduce transcription calls
            self.min_chunk_size = 16000 * 2 * 5  # 5 seconds
        elif latency_ms < 100:
            # Low latency: decrease buffer for faster transcription
            self.min_chunk_size = 16000 * 2 * 2  # 2 seconds
```

**3. Connection Pooling**
```python
# MongoDB connection pool (configured in db/mongo.py)
client = MongoClient(
    settings.MONGODB_URI,
    maxPoolSize=100,
    minPoolSize=10,
    maxIdleTimeMS=30000
)
```

### Frontend Optimizations

**1. Audio Queue Management**
```javascript
// Prevent audio overlap with queue
const audioQueue = useRef([]);
const isPlaying = useRef(false);

const playNextInQueue = async () => {
  if (isPlaying.current || audioQueue.current.length === 0) return;
  
  isPlaying.current = true;
  const audioData = audioQueue.current.shift();
  
  await playAudio(audioData);
  isPlaying.current = false;
  
  // Play next if queue not empty
  if (audioQueue.current.length > 0) {
    playNextInQueue();
  }
};

const enqueueAudio = (base64Audio) => {
  audioQueue.current.push(base64Audio);
  if (!isPlaying.current) {
    playNextInQueue();
  }
};
```

**2. Transcript Virtualization**
```javascript
// Use react-window for large transcripts (1000+ messages)
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={transcript.length}
  itemSize={80}
>
  {({ index, style }) => (
    <div style={style}>
      {transcript[index].text}
    </div>
  )}
</FixedSizeList>
```

**3. Debounce UI Updates**
```javascript
// Batch intelligence updates to reduce re-renders
const [intelligence, setIntelligence] = useState({});
const updateIntelligence = useCallback(
  debounce((newData) => {
    setIntelligence(prev => ({ ...prev, ...newData }));
  }, 200),
  []
);
```

---

## Mobile Optimization

### PWA Features

**manifest.json:**
```json
{
  "name": "HoneyBadger Live Call",
  "short_name": "HoneyCall",
  "start_url": "/live-call",
  "display": "standalone",
  "background_color": "#000000",
  "theme_color": "#3b82f6",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "orientation": "portrait"
}
```

### Mobile UI Optimizations

**Touch-Optimized Controls:**
```jsx
// Larger buttons for touch (min 44x44px)
<button className="w-16 h-16 rounded-full bg-red-500 touch-manipulation">
  <PhoneOff size={32} />
</button>
```

**Audio Context Unlock:**
```javascript
// iOS requires user interaction to unlock AudioContext
useEffect(() => {
  const unlockAudio = () => {
    const audioContext = new AudioContext();
    audioContext.resume();
    document.removeEventListener('touchstart', unlockAudio);
  };
  
  document.addEventListener('touchstart', unlockAudio);
}, []);
```

**Battery Optimization:**
```javascript
// Reduce transcription frequency on mobile
const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
const transcriptionInterval = isMobile ? 5000 : 3000;  // 5s vs 3s
```

---

## Summary

The **Live Call Architecture** is a sophisticated real-time communication system built on:

✅ **WebSocket-based bidirectional audio streaming**  
✅ **Server-side audio relay with transcription**  
✅ **AI-powered coaching using LangGraph + ElevenLabs TTS**  
✅ **Real-time intelligence extraction**  
✅ **Low-latency design** (<500ms end-to-end)  
✅ **Mobile-optimized** with PWA support  
✅ **Resilient error handling** with auto-reconnect  
✅ **Scalable architecture** ready for horizontal scaling  

This architecture enables operators to engage with scammers in real-time while receiving intelligent AI coaching, making it a powerful tool for scam research and evidence collection.

---

**Document Version:** 1.0  
**Last Updated:** February 21, 2026  
**Maintainer:** HoneyBadger Development Team
