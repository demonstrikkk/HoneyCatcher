# Voice-Enabled Agentic Honeypot - Implementation Plan

## 1. ARCHITECTURE OVERVIEW

### Core Principle
**Additive, Non-Breaking Extension**
- All existing text-based logic remains unchanged
- Voice is an I/O adapter layer on top of existing agent graph
- Text pipeline remains the source of truth

### Architecture Layers
```
┌─────────────────────────────────────────────────────────┐
│                  FRONTEND LAYER                         │
│  - Voice Recording UI                                   │
│  - Voice Playback Controls                              │
│  - AI Suggestion Display (Mode 2)                       │
│  - Enhanced Dashboard with Voice Filters                │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                   API LAYER                             │
│  - /api/voice/upload (audio chunk upload)               │
│  - /api/voice/transcribe (STT endpoint)                 │
│  - /api/voice/synthesize (TTS endpoint)                 │
│  - /api/voice/suggest (AI suggestion mode)              │
│  - Enhanced /api/sessions (voice metadata)              │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│               VOICE PROCESSING LAYER                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ STT Service │  │ TTS Service  │  │ Audio Utils  │   │
│  │ (Whisper)   │  │ (Piper/Coqui)│  │ (Chunking)   │   │
│  └─────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│          SPEECH NATURALIZATION LAYER (NEW)              │
│  - Converts AI text → spoken language                   │
│  - Adds filler words, natural pauses                    │
│  - Matches detected language/accent                     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│           EXISTING AGENT GRAPH (UNCHANGED)              │
│  Detection → Persona → Honeypot → Extraction → Callback │
└─────────────────────────────────────────────────────────┘
```

---

## 2. FOLDER STRUCTURE

```
honeypot/
├── backend/
│   ├── agents/
│   │   ├── graph.py                    # UNCHANGED (existing agent graph)
│   │   ├── prompts.py                  # ADD: Speech naturalization prompt
│   │   └── voice_adapter.py            # NEW: Voice I/O adapter node
│   │
│   ├── api/
│   │   ├── message.py                  # UNCHANGED
│   │   ├── sessions.py                 # UPDATE: Add voice metadata
│   │   └── voice.py                    # NEW: Voice endpoints
│   │
│   ├── services/
│   │   ├── scam_detector.py            # UNCHANGED
│   │   ├── intelligence_extractor.py   # UPDATE: Add audio entity extraction
│   │   ├── callback.py                 # UNCHANGED
│   │   ├── stt_service.py              # NEW: Speech-to-Text (Whisper)
│   │   ├── tts_service.py              # NEW: Text-to-Speech (Piper/Coqui)
│   │   └── audio_processor.py          # NEW: Audio chunking, validation
│   │
│   ├── db/
│   │   └── models.py                   # UPDATE: Add voice fields to Session/Message
│   │
│   └── requirements.txt                # UPDATE: Add audio dependencies
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── VoiceRecorder.jsx       # NEW: Audio recording component
    │   │   ├── VoicePlayer.jsx         # NEW: Audio playback component
    │   │   ├── AISuggestionPanel.jsx   # NEW: Mode 2 suggestion display
    │   │   └── DashboardFilters.jsx    # NEW: Advanced filters
    │   │
    │   ├── pages/
    │   │   ├── Dashboard.jsx           # UPDATE: Add voice insights
    │   │   ├── SessionView.jsx         # UPDATE: Audio timeline display
    │   │   └── VoicePlayground.jsx     # NEW: Voice testing interface
    │   │
    │   └── services/
    │       └── voiceApi.js             # NEW: Voice API client
```

---

## 3. DATA MODELS

### Updated Session Model
```python
class Session(BaseModel):
    # Existing fields (UNCHANGED)
    session_id: str
    is_confirmed_scam: bool = False
    scam_score: float = 0.0
    status: str = "active"
    message_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # NEW: Voice-specific fields
    voice_enabled: bool = False
    detected_language: Optional[str] = None  # From Whisper
    voice_mode: str = "text"  # "text" | "ai_speaks" | "ai_suggests"
    audio_chunk_count: int = 0
    total_audio_duration: float = 0.0  # seconds
```

### Updated Message Model
```python
class Message(BaseModel):
    # Existing fields (UNCHANGED)
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    sender: str  # "scammer" | "agent"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = {}
    
    # NEW: Voice-specific fields
    is_voice: bool = False
    audio_file_path: Optional[str] = None
    transcription_confidence: Optional[float] = None
    speech_naturalized: bool = False  # For agent responses
```

### New VoiceChunk Model
```python
class VoiceChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    audio_data: bytes  # Raw audio bytes
    format: str = "wav"  # wav, mp3, etc.
    sample_rate: int = 16000
    duration: float  # seconds
    sequence_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = False
```

---

## 4. API ENDPOINTS (NEW/UPDATED)

### NEW: Voice Endpoints

#### 1. `POST /api/voice/upload`
**Purpose**: Upload audio chunk from client
```json
Request:
{
  "sessionId": "uuid",
  "audioData": "base64_encoded_audio",
  "format": "wav",
  "sequenceNumber": 1,
  "metadata": {"sampleRate": 16000, "duration": 2.5}
}

Response:
{
  "status": "success",
  "chunkId": "uuid",
  "sessionId": "uuid"
}
```

#### 2. `POST /api/voice/transcribe`
**Purpose**: Transcribe audio chunk → text
```json
Request:
{
  "chunkId": "uuid",
  "sessionId": "uuid"
}

Response:
{
  "status": "success",
  "transcription": "text output",
  "confidence": 0.95,
  "detectedLanguage": "en",
  "duration": 2.5
}
```

#### 3. `POST /api/voice/synthesize`
**Purpose**: Generate voice from AI response
```json
Request:
{
  "sessionId": "uuid",
  "text": "AI response text",
  "language": "en",
  "voiceMode": "ai_speaks"  // or "ai_suggests"
}

Response (ai_speaks):
{
  "status": "success",
  "audioUrl": "/audio/uuid.wav",
  "naturalizedText": "Uh, actually yeah...",
  "duration": 3.2
}

Response (ai_suggests):
{
  "status": "success",
  "suggestion": "Uh, actually yeah...",
  "originalText": "Yes, I understand"
}
```

#### 4. `POST /api/voice/process-stream`
**Purpose**: Process continuous audio stream (Real-time)
```json
Request (WebSocket or chunked):
{
  "sessionId": "uuid",
  "audioChunk": "base64",
  "timestamp": 1234567890
}

Response (Stream):
{
  "partialTranscription": "Hello, I am...",
  "isFinal": false
}
```

### UPDATED: Sessions Endpoint

#### `GET /api/sessions?filters=...`
**New Query Params**:
- `voiceEnabled=true|false`
- `language=en|hi|ta|...`
- `scamType=phishing|impersonation|...`
- `confidenceMin=0.8`
- `hasExtractedEntities=true`
- `voiceMode=ai_speaks|ai_suggests`

**Response**: Enhanced with voice metadata
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "voice_enabled": true,
      "detected_language": "hi",
      "voice_mode": "ai_suggests",
      "audio_chunk_count": 12,
      "total_audio_duration": 45.3,
      // ... existing fields
    }
  ],
  "totalCount": 100,
  "filters": {...}
}
```

---

## 5. IMPLEMENTATION PHASES

### Phase 1: Audio Infrastructure (Backend Core)
**Goal**: Set up audio processing pipeline

1. **Install Dependencies**
   - `faster-whisper` (STT)
   - `piper-tts` or `TTS` (Coqui) (TTS)
   - `pydub` (audio manipulation)
   - `numpy` (audio processing)

2. **Create Audio Services**
   - `stt_service.py`: Whisper integration
   - `tts_service.py`: Piper/Coqui integration
   - `audio_processor.py`: Chunking, validation, format conversion

3. **Database Updates**
   - Update `models.py` with voice fields
   - Create migration logic (soft update)

### Phase 2: Speech Naturalization Layer
**Goal**: Make AI responses sound human

1. **Create Speech Prompt**
   - Add `SPEECH_NATURALIZATION_PROMPT` to `prompts.py`
   - Context-aware filler words
   - Language-specific naturalizations

2. **Add Voice Adapter Node**
   - `voice_adapter.py`: Pre/post-processing for agent graph
   - Input: Audio → Transcription → Text
   - Output: Text → Speech-naturalized text → Audio

3. **Update Agent Graph (Minimal)**
   - Add optional voice processing hooks
   - NO changes to core detection/engagement logic

### Phase 3: API Layer
**Goal**: Expose voice capabilities via REST

1. **Create Voice API Router**
   - Implement all 4 endpoints
   - Audio upload handling
   - Background task integration

2. **Update Session API**
   - Add voice metadata fields
   - Implement filtering
   - Return voice insights

3. **Background Intelligence**
   - Extract entities from transcriptions
   - Parallel regex + LLM extraction
   - Aggregate results per session

### Phase 4: Frontend Voice UI
**Goal**: Voice recording and playback

1. **Voice Recorder Component**
   - Browser MediaRecorder API
   - Chunk-based upload (2-3 sec chunks)
   - Real-time feedback

2. **Voice Player Component**
   - Audio playback with timeline
   - Transcript sync
   - Highlighted entities

3. **AI Suggestion Panel (Mode 2)**
   - Display AI-generated speech text
   - Copy-to-clipboard
   - "Speak it" button

### Phase 5: Dashboard Upgrade
**Goal**: Voice insights and filtering

1. **Enhanced Filters**
   - Language dropdown
   - Scam type multi-select
   - Confidence slider
   - Voice mode toggle

2. **Voice Metrics**
   - Total audio duration
   - Avg transcription confidence
   - Language distribution
   - Voice vs text success rate

3. **Session Detail Enhancements**
   - Audio timeline
   - Transcript with timestamps
   - Extracted entities highlight

### Phase 6: Testing & Validation
**Goal**: Production-ready robustness

1. **Unit Tests**
   - STT/TTS service mocks
   - Audio chunking logic
   - Speech naturalization

2. **Integration Tests**
   - Full voice flow (upload → transcribe → agent → synthesize)
   - Fallback scenarios (LLM unavailable)

3. **Performance Tests**
   - Latency benchmarks (target: <2s end-to-end)
   - Memory usage (chunking prevents overload)

---

## 6. KEY DESIGN DECISIONS

### Why Faster-Whisper (not OpenAI Whisper API)?
- **Offline**: No external API dependency
- **Fast**: Optimized C++ implementation
- **Language detection**: Built-in, supports 99 languages
- **Cost**: Free

### Why Piper TTS (not cloud TTS)?
- **Latency**: Local inference (<500ms)
- **Multilingual**: Supports common languages
- **Quality**: Natural-sounding voices
- **Cost**: Free

### Why Chunking (2-3 sec)?
- **Low latency**: Incremental processing
- **Memory efficient**: No full audio buffering
- **Conversational**: Simulates real-time dialogue

### Why Speech Naturalization Layer?
- **Critical insight**: LLMs generate written language, not spoken
- **Human-sounding**: Filler words, contractions, pauses
- **Language-aware**: Different patterns for Hindi vs English

### Why Two Modes (AI speaks vs AI suggests)?
- **Ethics**: Some users uncomfortable with full automation
- **Privacy**: Gives control back to user
- **Flexibility**: Supports different use cases

---

## 7. RISK MITIGATION

### Risk 1: Audio Quality Issues
**Mitigation**:
- Accept multiple formats (wav, mp3, webm)
- Automatic resampling to 16kHz mono
- Noise reduction (Whisper handles this)

### Risk 2: Latency >2s
**Mitigation**:
- Background transcription (async)
- Pre-loaded TTS models
- Chunked processing

### Risk 3: Language Mismatch
**Mitigation**:
- Whisper detects language automatically
- TTS voice selected dynamically
- Fallback to detected language if specified language unavailable

### Risk 4: LLM Unavailable
**Mitigation**:
- Speech naturalization uses same LLM fallback logic
- Simple rule-based naturalization as last resort

### Risk 5: Storage Explosion (Audio Files)
**Mitigation**:
- Audio stored only for confirmed scams
- Compression (MP3, 32kbps sufficient for voice)
- TTL-based cleanup (delete after 30 days)

---

## 8. TESTING STRATEGY

### Manual Testing Checklist
- [ ] Record 2-sec audio chunk → Verify transcription
- [ ] Send transcribed text to agent → Verify response
- [ ] Synthesize agent response → Verify audio playback
- [ ] Test Hindi/English/Tamil languages
- [ ] Test both AI modes (speaks vs suggests)
- [ ] Test dashboard filters
- [ ] Test session detail audio timeline

### Automated Testing
- Unit tests for each service
- Integration test: Full voice loop
- Fallback tests: LLM unavailable scenarios

---

## 9. SUCCESS CRITERIA

✅ Voice input transcribed with >90% confidence
✅ Agent response synthesized in <2 seconds
✅ Speech sounds natural (filler words, pauses)
✅ Multilingual support (3+ languages)
✅ Both AI modes functional
✅ Dashboard filters working
✅ No regression in existing text pipeline
✅ Zero breaking changes to API schema

---

## 10. DEPLOYMENT NOTES

### Backend Requirements
- Python 3.10+
- ffmpeg (for audio processing)
- 2GB RAM minimum (for Whisper model)

### Frontend Requirements
- Browser with MediaRecorder API support
- Microphone permissions

### Environment Variables (New)
```env
# Voice Services
WHISPER_MODEL=base  # tiny, base, small, medium, large
TTS_ENGINE=piper  # piper or coqui
TTS_VOICE_PATH=./models/voices/
AUDIO_STORAGE_PATH=./storage/audio/
AUDIO_CHUNK_SIZE=2  # seconds
```

---

## CONCLUSION

This upgrade transforms the honeypot into a **voice-enabled, multilingual, human-sounding system** while:
- ✅ Maintaining 100% backward compatibility
- ✅ Keeping text as source of truth
- ✅ Adding zero breaking changes
- ✅ Following enterprise production standards

**Next Steps**: Implement Phase 1 (Audio Infrastructure)
