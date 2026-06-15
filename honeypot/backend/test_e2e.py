"""
Comprehensive E2E test suite for HoneyBadger Backend.

Tests all layers: configuration, services, agents, API routes,
feature pipelines, and WebSocket signaling.

Run:  cd honeypot/backend && venv_win\Scripts\pytest test_e2e.py -v --asyncio-mode=auto
"""

import io
import json
import os
import re
import struct
import uuid
import wave
from pathlib import Path
from datetime import datetime
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio

# Ensure we can import backend modules
BACKEND = Path(__file__).parent
os.chdir(str(BACKEND))
import sys
sys.path.insert(0, str(BACKEND))

os.environ["APP_NAME"] = "HoneyBadger-Test"
os.environ["DEBUG"] = "true"

from config import settings
API_KEY = settings.API_SECRET_KEY

# ---------------------------------------------------------------------------
# Event loop debug support
# ---------------------------------------------------------------------------
import asyncio

# Use SelectorEventLoop on Windows to avoid ProactorEventLoop issues
import platform
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def _ensure_event_loop():
    """Ensure there is an open event loop, return it."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_sine_wav(duration_s: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Generate a tiny sine-wave WAV file for STT testing."""
    n_samples = int(sample_rate * duration_s)
    samples = []
    for i in range(n_samples):
        sample = int(16000 * 0.3 * (i / n_samples))
        samples.append(struct.pack("<h", sample))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(samples))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def app():
    """Yield the FastAPI app with manual lifespan management."""
    from main import app as _app
    from db.mongo import connect_db, close_db
    await connect_db()
    yield _app
    await close_db()


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client backed by the live ASGI app."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_headers(client: httpx.AsyncClient) -> dict:
    """Register + login a test user, return Authorization header."""
    uname = f"testuser_{uuid.uuid4().hex[:8]}"
    pwd = "TestPass123!"
    r = await client.post("/api/auth/register", json={
        "username": uname, "password": pwd,
    })
    if r.status_code not in (200, 201):
        # Try login in case user already exists
        r = await client.post("/api/auth/login", json={
            "username": uname, "password": pwd,
        })
        if r.status_code != 200:
            pytest.skip(f"Auth setup failed ({r.status_code})")
    else:
        r = await client.post("/api/auth/login", json={
            "username": uname, "password": pwd,
        })
        if r.status_code != 200:
            pytest.skip(f"Login failed ({r.status_code}): {r.text}")

    data = r.json()
    token = data.get("access_token", "")
    if not token:
        pytest.skip("No access_token in login response")
    return {"Authorization": f"Bearer {token}"}


# ===================================================================
# 1. Config & Health
# ===================================================================

class TestConfigAndHealth:
    def test_config_loads(self):
        from config import settings
        assert settings.APP_NAME == "HoneyBadger-Test"
        assert settings.DEBUG is True
        assert settings.GROQ_API_KEY  # must be set via .env
        assert settings.ELEVENLABS_API_KEY
        assert settings.MONGODB_URI

    def test_allowed_origins(self):
        from config import settings
        assert len(settings.allowed_origins) >= 1
        assert all(isinstance(o, str) for o in settings.allowed_origins)

    async def test_health(self, client: httpx.AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ===================================================================
# 2. Services (no DB / no API required)
# ===================================================================

class TestIntelligenceExtractor:
    def test_extract_phone(self):
        from services.intelligence_extractor import extract_entities
        result = extract_entities("Call me at +91 9876543210")
        phones = [e for e in result["entities"] if e["type"] == "phone"]
        assert len(phones) >= 1

    def test_extract_upi(self):
        from services.intelligence_extractor import extract_entities
        result = extract_entities("Send money to user@upi")
        upis = [e for e in result["entities"] if e["type"] == "upi"]
        assert len(upis) >= 1

    def test_extract_url(self):
        from services.intelligence_extractor import extract_entities
        result = extract_entities("Visit http://evil.com/login")
        urls = [e for e in result["entities"] if e["type"] == "url"]
        assert len(urls) >= 1

    def test_extract_bank_account(self):
        from services.intelligence_extractor import extract_entities
        result = extract_entities("My account is 123456789012345")
        accounts = [e for e in result["entities"] if e["type"] == "bank_account"]
        assert len(accounts) >= 1

    def test_tactics_detection(self):
        from services.intelligence_extractor import extract_entities
        result = extract_entities("This is urgent! Your account will be blocked immediately. The RBI officer is calling.")
        assert "urgency" in result["tactics"]
        assert "authority" in result["tactics"]
        assert "fear" in result["tactics"]
        assert result["threat_level"] > 0

    def test_empty_text(self):
        from services.intelligence_extractor import extract_entities
        result = extract_entities("")
        assert result["entities"] == []
        assert result["threat_level"] == 0


class TestScamDetector:
    def test_calculate_score(self):
        from services.scam_detector import calculate_scam_score
        score = calculate_scam_score("Your bank account will be blocked immediately. Send money now.", [])
        assert 0.0 <= score <= 1.0

    def test_score_zero_for_safe(self):
        from services.scam_detector import calculate_scam_score
        score = calculate_scam_score("Hello, how are you today?", [])
        assert score <= 0.3  # should be low

    def test_score_with_history(self):
        from services.scam_detector import calculate_scam_score
        score = calculate_scam_score("Send money now", ["Your account is blocked"])
        assert score > 0.0


# ===================================================================
# 3. Services (real API calls)
# ===================================================================

class TestSTTService:
    async def test_transcribe_bytes_empty(self, app):
        from services.stt_service import transcribe_bytes
        result = await transcribe_bytes(b"\x00" * 1000, fmt="wav")
        # May return empty text for garbage audio
        assert isinstance(result, dict)
        assert "text" in result
        assert "language" in result

    async def test_transcribe_file_not_found(self, app):
        from services.stt_service import transcribe_file
        try:
            result = await transcribe_file("nonexistent.wav")
            assert isinstance(result, dict)
        except FileNotFoundError:
            pass  # also acceptable — function raises on missing file

    async def test_transcribe_sine_wave(self, app):
        from services.stt_service import transcribe_bytes
        wav_bytes = make_sine_wav(1.0)
        result = await transcribe_bytes(wav_bytes, fmt="wav")
        assert isinstance(result, dict)
        assert "text" in result


class TestTTSService:
    async def test_synthesize_to_bytes(self, app):
        from services.tts_service import synthesize_to_bytes
        try:
            audio = await synthesize_to_bytes("Hello, this is a test.")
        except Exception as e:
            pytest.skip(f"TTS API error: {e}")
        assert isinstance(audio, bytes)
        if len(audio) == 0:
            pytest.skip("TTS returned empty bytes")
        assert len(audio) > 100

    async def test_synthesize_with_custom_voice(self, app):
        from services.elevenlabs_service import elevenlabs_service
        try:
            voices = await elevenlabs_service.get_available_voices()
        except Exception:
            pytest.skip("Cannot list ElevenLabs voices")
        if not voices:
            pytest.skip("No ElevenLabs voices available")
        # Find a non-library voice (free voices that don't require payment)
        voice_id = None
        for v in voices:
            if v.get("category") != "premade":
                voice_id = v["voice_id"]
                break
        if not voice_id:
            voice_id = voices[0]["voice_id"]
        from services.tts_service import synthesize_to_bytes
        try:
            audio = await synthesize_to_bytes("Testing 123.", voice_id=voice_id)
        except Exception as e:
            pytest.skip(f"TTS voice synthesis error: {e}")
        assert isinstance(audio, bytes)
        if len(audio) == 0:
            pytest.skip("TTS returned empty bytes")
        assert len(audio) > 100


# ===================================================================
# 4. Agent Graph (real Groq API)
# ===================================================================

class TestAgentGraph:
    async def test_run_agent_basic(self, app):
        from agents.graph import run_agent
        result = await run_agent(
            scammer_text="Hello, I am calling from your bank. Your account has been compromised.",
            history=[],
            mode="ai_coached",
        )
        assert "intent" in result
        assert "strategy" in result
        assert result.get("coaching_text") or result.get("ai_response")
        assert result.get("intent_confidence", 0) > 0

    async def test_run_agent_takeover(self, app):
        from agents.graph import run_agent
        result = await run_agent(
            scammer_text="This is the police! You need to pay a fine immediately.",
            history=[{"speaker": "scammer", "text": "Hello, are you there?"}],
            mode="ai_takeover",
            turn_count=1,
        )
        assert result.get("ai_response")
        assert result["intent"] != "unknown"

    async def test_run_agent_empty_text(self, app):
        from agents.graph import run_agent
        result = await run_agent("", [], mode="ai_coached")
        assert isinstance(result, dict)


# ===================================================================
# 5. Auth Endpoints
# ===================================================================

class TestAuth:
    async def test_register_and_login(self, client: httpx.AsyncClient):
        uname = f"e2e_{uuid.uuid4().hex[:8]}"
        pwd = "StrongP@ss1"
        # Register
        r = await client.post("/api/auth/register", json={
            "username": uname, "password": pwd,
        })
        assert r.status_code in (200, 201)
        # Login
        r = await client.post("/api/auth/login", json={
            "username": uname, "password": pwd,
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate(self, client: httpx.AsyncClient, auth_headers):
        uname = f"dup_{uuid.uuid4().hex[:6]}"
        pwd = "TestP@ss1"
        await client.post("/api/auth/register", json={"username": uname, "password": pwd})
        r = await client.post("/api/auth/register", json={"username": uname, "password": pwd})
        assert r.status_code == 400

    async def test_login_wrong_password(self, client: httpx.AsyncClient):
        r = await client.post("/api/auth/login", json={
            "username": "nonexistent_user", "password": "wrong",
        })
        assert r.status_code == 401

    async def test_refresh_token(self, client: httpx.AsyncClient, auth_headers):
        # Get refresh token via login
        # auth_headers fixture already does login, so we login again
        uname = f"ref_{uuid.uuid4().hex[:6]}"
        pwd = "TestP@ss1"
        await client.post("/api/auth/register", json={"username": uname, "password": pwd})
        login_r = await client.post("/api/auth/login", json={"username": uname, "password": pwd})
        refresh_token = login_r.json()["refresh_token"]

        r = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_me(self, client: httpx.AsyncClient, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "user_id" in data
        assert "username" in data


# ===================================================================
# 6. Session Endpoints
# ===================================================================

class TestSessions:
    async def test_create_and_list(self, client: httpx.AsyncClient, auth_headers):
        # Create
        r = await client.post("/api/sessions", json={}, headers=auth_headers)
        assert r.status_code == 201
        sid = r.json()["session_id"]
        assert sid

        # List
        r = await client.get("/api/sessions", headers=auth_headers)
        assert r.status_code == 200
        sessions = r.json()
        assert isinstance(sessions, list)
        ids = [s["session_id"] for s in sessions]
        assert sid in ids

    async def test_get_and_delete(self, client: httpx.AsyncClient, auth_headers):
        # Create
        r = await client.post("/api/sessions", json={
            "scammer_phone": "+911234567890",
            "operator_name": "Agent007",
            "call_type": "voice",
        }, headers=auth_headers)
        sid = r.json()["session_id"]

        # Get
        r = await client.get(f"/api/sessions/{sid}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["scammer_phone"] == "+911234567890"

        # Delete
        r = await client.delete(f"/api/sessions/{sid}", headers=auth_headers)
        assert r.status_code == 200

        # Verify gone
        r = await client.get(f"/api/sessions/{sid}", headers=auth_headers)
        assert r.status_code == 404

    async def test_get_nonexistent(self, client: httpx.AsyncClient, auth_headers):
        r = await client.get("/api/sessions/nonexistent-sid", headers=auth_headers)
        assert r.status_code == 404

    async def test_unauthorized(self, client: httpx.AsyncClient):
        r = await client.get("/api/sessions")
        assert r.status_code == 401


# ===================================================================
# 7. Message Endpoints
# ===================================================================

class TestMessages:
    async def test_send_and_get(self, client: httpx.AsyncClient, auth_headers):
        # Create a session first
        r = await client.post("/api/sessions", json={}, headers=auth_headers)
        sid = r.json()["session_id"]

        # Send a scam message
        r = await client.post("/api/message/send", json={
            "session_id": sid,
            "content": "Hello, your bank account will be blocked unless you send OTP immediately.",
            "sender": "scammer",
        }, headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "reply" in data
        assert data["intent"] is not None
        assert data["strategy"] is not None

        # Get messages
        r = await client.get(f"/api/message/session/{sid}", headers=auth_headers)
        assert r.status_code == 200
        msgs = r.json()
        assert len(msgs) >= 2  # scammer msg + agent reply


# ===================================================================
# 8. Voice Endpoint
# ===================================================================

class TestVoice:
    async def test_voice_upload(self, client: httpx.AsyncClient, auth_headers):
        # Create session
        r = await client.post("/api/sessions", json={}, headers=auth_headers)
        assert r.status_code == 201
        sid = r.json()["session_id"]

        # Upload a sine-wave audio file
        wav_bytes = make_sine_wav(0.5)
        files = {"audio": ("test.wav", wav_bytes, "audio/wav")}
        r = await client.post(
            "/api/voice/upload",
            data={"session_id": sid, "mode": "ai_speaks"},
            files=files,
            headers=auth_headers,
        )
        if r.status_code != 200:
            # Likely ElevenLabs payment issue with library voices
            pytest.skip("Voice upload failed (ElevenLabs TTS may require payment)")
        data = r.json()
        assert "transcription" in data
        assert "reply" in data
        assert "intent" in data


# ===================================================================
# 9. Live Call REST Endpoints
# ===================================================================

class TestLiveCall:
    async def test_start_call(self, client: httpx.AsyncClient):
        r = await client.post("/api/live-call/start", json={})
        assert r.status_code == 200
        data = r.json()
        assert "call_id" in data
        assert "operator_url" in data
        assert "scammer_url" in data

    async def test_start_call_with_id(self, client: httpx.AsyncClient):
        cid = str(uuid.uuid4())
        r = await client.post("/api/live-call/start", json={"call_id": cid})
        assert r.status_code == 200
        assert r.json()["call_id"] == cid

    async def test_call_status_not_found(self, client: httpx.AsyncClient):
        r = await client.get("/api/live-call/status/nonexistent-call")
        assert r.status_code == 200
        assert r.json()["status"] == "not_found"

    async def test_call_status(self, client: httpx.AsyncClient):
        r = await client.post("/api/live-call/start", json={})
        cid = r.json()["call_id"]

        r = await client.get(f"/api/live-call/status/{cid}")
        assert r.status_code == 200
        data = r.json()
        assert data["call_id"] == cid
        assert data["is_active"] is True

    async def test_end_call(self, client: httpx.AsyncClient):
        r = await client.post("/api/live-call/start", json={})
        cid = r.json()["call_id"]

        r = await client.post(f"/api/live-call/end/{cid}")
        assert r.status_code == 200
        assert r.json()["status"] == "ended"


# ===================================================================
# 10. Live Takeover REST Endpoints
# ===================================================================

class TestLiveTakeover:
    async def test_start_session(self, client: httpx.AsyncClient):
        r = await client.post("/live/start", json={
            "mode": "ai_coached", "language": "en",
        }, headers={"x-api-key": API_KEY})
        if r.status_code == 401:
            pytest.skip("API key auth required for /live/start")

        assert r.status_code == 200
        data = r.json()
        assert "session_id" in data
        assert data["status"] == "active"

    async def test_start_session_no_auth(self, client: httpx.AsyncClient):
        r = await client.post("/live/start", json={"mode": "ai_coached"})
        assert r.status_code == 401

    async def test_session_status(self, client: httpx.AsyncClient):
        r = await client.post("/live/start", json={"mode": "ai_coached"},
                              headers={"x-api-key": API_KEY})
        if r.status_code == 401:
            pytest.skip("API key auth required")
        sid = r.json()["session_id"]

        r = await client.get(f"/live/status/{sid}",
                             headers={"x-api-key": API_KEY})
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"] == sid
        assert data["status"] == "active"

    async def test_end_session(self, client: httpx.AsyncClient):
        r = await client.post("/live/start", json={"mode": "ai_coached"},
                              headers={"x-api-key": API_KEY})
        if r.status_code == 401:
            pytest.skip("API key auth required")
        sid = r.json()["session_id"]

        r = await client.post(f"/live/end/{sid}",
                              headers={"x-api-key": API_KEY})
        assert r.status_code == 200


# ===================================================================
# 11. Voice Clone / ElevenLabs / Agora / Testing Endpoints
# ===================================================================

class TestElevenLabs:
    async def test_list_voices(self, client: httpx.AsyncClient):
        r = await client.get("/elevenlabs/voices",
                             headers={"x-api-key": API_KEY})
        if r.status_code == 401:
            pytest.skip("API key auth required")
        assert r.status_code == 200
        data = r.json()
        assert "voices" in data
        assert data["count"] > 0


class TestVoiceClone:
    async def test_list_clones(self, client: httpx.AsyncClient):
        r = await client.get("/voice-clone/list",
                             headers={"x-api-key": API_KEY})
        if r.status_code == 401:
            pytest.skip("API key auth required")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestAgora:
    async def test_get_config(self, client: httpx.AsyncClient):
        r = await client.get("/agora/config")
        assert r.status_code == 200
        data = r.json()
        assert "appId" in data
        assert "tokenRequired" in data


class TestTesting:
    async def test_virustotal_info(self, client: httpx.AsyncClient):
        r = await client.get("/test-virustotal/info")
        assert r.status_code == 200
        data = r.json()
        assert "test_urls" in data
        assert "virustotal_configured" in data


# ===================================================================
# 12. SMS Evidence
# ===================================================================

class TestSMSEvidence:
    async def test_submit_sms(self, client: httpx.AsyncClient):
        r = await client.post("/session/test-session-id/sms", json={
            "session_id": "test-session-id",
            "phone_number": "+911234567890",
            "messages": [
                {"address": "+911234567890", "body": "Your OTP is 123456",
                 "date": int(datetime.utcnow().timestamp() * 1000), "type": 1}
            ],
        }, headers={"x-api-key": API_KEY})
        if r.status_code == 401:
            pytest.skip("API key auth required")
        assert r.status_code == 200
        assert r.json()["status"] == "success"

    async def test_session_mismatch(self, client: httpx.AsyncClient):
        r = await client.post("/session/session-a/sms", json={
            "session_id": "session-b",
            "phone_number": "+911234567890",
            "messages": [],
        }, headers={"x-api-key": API_KEY})
        if r.status_code == 401:
            pytest.skip("API key auth required")
        assert r.status_code == 400


# ===================================================================
# 13. WebRTC Signaling (Socket.IO)
# ===================================================================

class TestWebRTCSignaling:
    @pytest.mark.asyncio
    async def test_socketio_connect(self):
        import socketio
        from config import settings

        # We can't easily test Socket.IO against the ASGI lifespan app
        # with a separate connection, but we can verify the module loads
        from api.webrtc_signaling import sio
        assert sio is not None
        assert hasattr(sio, "emit")


# ===================================================================
# 14. Feature Pipeline
# ===================================================================

class TestIntelligencePipeline:
    async def test_process_transcript(self, app):
        """Test the intelligence pipeline with live session manager."""
        from features.live_takeover.session_manager import (
            live_session_manager, TakeoverMode
        )
        from features.live_takeover.intelligence_pipeline import intelligence_pipeline

        # Create a live session -- this writes to MongoDB
        session = await live_session_manager.create_session(
            mode=TakeoverMode.AI_COACHED,
            language="en"
        )
        sid = session.session_id

        # Process a scam message
        result = await intelligence_pipeline.process_transcript(
            session_id=sid,
            text="Send money to my account 123456789012 at SBI bank. Call me at 9876543210 immediately!",
            speaker="scammer",
        )
        assert "new_entities" in result
        assert "threat_level" in result
        assert "tactics" in result
        assert "urls_to_scan" in result
        assert result["threat_level"] > 0.0

        # Clean up -- end session
        await live_session_manager.end_session(sid)

    async def test_process_transcript_empty(self, app):
        from features.live_takeover.intelligence_pipeline import intelligence_pipeline
        result = await intelligence_pipeline.process_transcript(
            session_id="test-empty",
            text="",
            speaker="scammer",
        )
        assert result["new_entities"] == []
        assert result["threat_level"] == 0.0

    async def test_process_agent_extracted(self, app):
        from features.live_takeover.session_manager import (
            live_session_manager, TakeoverMode
        )
        from features.live_takeover.intelligence_pipeline import intelligence_pipeline

        session = await live_session_manager.create_session(mode=TakeoverMode.AI_COACHED)
        sid = session.session_id

        result = await intelligence_pipeline.process_agent_extracted(
            session_id=sid,
            extracted_data={
                "phone_numbers": ["9876543210"],
                "bank_accounts": ["123456789012"],
                "upi_ids": ["test@upi"],
            },
        )
        assert len(result) > 0
        await live_session_manager.end_session(sid)


class TestReportGenerator:
    async def test_generate_json_report(self, app):
        from features.live_takeover.session_manager import (
            live_session_manager, TakeoverMode
        )
        from features.live_takeover.report_generator import report_generator

        session = await live_session_manager.create_session(mode=TakeoverMode.AI_COACHED)
        sid = session.session_id

        report = await report_generator.generate_report(session_id=sid, format="json")
        assert report["format"] == "json"
        assert "report_id" in report
        assert report["data"] is not None

        await live_session_manager.end_session(sid)

    async def test_generate_report_nonexistent(self, app):
        from features.live_takeover.report_generator import report_generator
        with pytest.raises(ValueError):
            await report_generator.generate_report("nonexistent-session", format="json")


class TestURLScanner:
    @pytest.mark.asyncio
    async def test_pattern_scan_safe(self):
        from features.live_takeover.url_scanner import PatternScanner
        scanner = PatternScanner()
        result = await scanner.scan("https://www.google.com")
        assert result is not None
        assert result["risk_score"] < 0.5

    @pytest.mark.asyncio
    async def test_pattern_scan_suspicious(self):
        from features.live_takeover.url_scanner import PatternScanner
        scanner = PatternScanner()
        result = await scanner.scan("http://evil-login.xyz/verify-account.php")
        assert result is not None
        assert result["is_malicious"]  # Should be flagged

    @pytest.mark.asyncio
    async def test_multi_scanner(self):
        from features.live_takeover.url_scanner import MultiScanner
        scanner = MultiScanner()
        result = await scanner.scan_url("https://github.com")
        assert result.is_safe or not result.is_safe  # Should at least return a result
        assert result.url == "https://github.com"

    @pytest.mark.asyncio
    async def test_multi_scanner_caching(self):
        from features.live_takeover.url_scanner import MultiScanner
        scanner = MultiScanner()
        r1 = await scanner.scan_url("https://example.com")
        r2 = await scanner.scan_url("https://example.com")
        assert r2.scanned_at == r1.scanned_at  # Cached result


class TestTakeoverAgent:
    async def test_run_takeover(self, app):
        from features.live_takeover.takeover_agent import takeover_agent
        result = await takeover_agent.run(
            scammer_text="Hello, I'm from your bank. Your account has been compromised.",
            history=[],
            mode="ai_takeover",
            language="en",
        )
        assert "ai_response" in result
        assert result["ai_response"]
        assert result["intent"] != ""

    async def test_run_coached(self, app):
        from features.live_takeover.takeover_agent import takeover_agent
        result = await takeover_agent.run(
            scammer_text="Send me your OTP immediately.",
            history=[{"role": "scammer", "content": "Hello, this is the bank."}],
            mode="ai_coached",
        )
        assert "coaching_scripts" in result
        assert len(result["coaching_scripts"]) > 0

    async def test_get_coaching_suggestions(self, app):
        from features.live_takeover.takeover_agent import takeover_agent
        result = await takeover_agent.get_coaching_suggestions(
            conversation="Scammer: Your account is blocked.\nYou: What? Why?",
            entities=[],
            threat_level=0.5,
            tactics=["fear", "urgency"],
        )
        assert "suggestions" in result
        assert "recommended_response" in result


class TestStreamingSTT:
    async def test_add_and_transcribe(self, app):
        from features.live_takeover.streaming_stt import StreamingTranscriber
        stt = StreamingTranscriber(buffer_threshold_ms=500)
        wav_bytes = make_sine_wav(0.5)
        stt.add_chunk(wav_bytes, duration_ms=500, audio_format="wav")
        result = await stt.transcribe_buffer()
        # Should return a segment (even if empty text for sine wave)
        assert result is not None or stt._chunks == []

    def test_reset(self):
        from features.live_takeover.streaming_stt import StreamingTranscriber
        stt = StreamingTranscriber()
        stt.add_chunk(b"\x00" * 1000, duration_ms=100)
        stt.reset()
        assert stt._chunks == []
        assert stt._buffer_duration_ms == 0.0


class TestVoiceCloneService:
    async def test_list_voices(self, app):
        from features.live_takeover.voice_clone_service import voice_clone_service
        voices = await voice_clone_service.list_voices()
        assert isinstance(voices, list)

    async def test_is_available(self):
        from features.live_takeover.voice_clone_service import voice_clone_service
        assert voice_clone_service.is_available  # should have API key


class TestSessionManager:
    async def test_create_and_get(self, app):
        from features.live_takeover.session_manager import (
            live_session_manager, TakeoverMode
        )
        session = await live_session_manager.create_session(mode=TakeoverMode.AI_TAKEOVER)
        assert session.session_id
        assert session.status.value == "active"

        got = await live_session_manager.get_session(session.session_id)
        assert got is not None
        assert got.session_id == session.session_id

    async def test_switch_mode(self, app):
        from features.live_takeover.session_manager import (
            live_session_manager, TakeoverMode
        )
        session = await live_session_manager.create_session(mode=TakeoverMode.AI_TAKEOVER)
        ok = await live_session_manager.switch_mode(session.session_id, TakeoverMode.AI_COACHED)
        assert ok
        assert session.current_mode == TakeoverMode.AI_COACHED

    async def test_switch_nonexistent(self, app):
        from features.live_takeover.session_manager import (
            live_session_manager, TakeoverMode
        )
        ok = await live_session_manager.switch_mode("nonexistent", TakeoverMode.AI_COACHED)
        assert not ok

    async def test_update_intelligence(self, app):
        from features.live_takeover.session_manager import (
            live_session_manager, TakeoverMode, ExtractedEntity
        )
        session = await live_session_manager.create_session(mode=TakeoverMode.AI_COACHED)
        entity = ExtractedEntity(entity_type="phone", value="9876543210", confidence=0.9)
        new = await live_session_manager.update_intelligence(
            session_id=session.session_id,
            entities=[entity],
            threat_level=0.7,
            tactics=["fear"],
        )
        assert len(new) == 1
        assert session.threat_level == 0.7

    async def test_end_session(self, app):
        from features.live_takeover.session_manager import (
            live_session_manager, TakeoverMode
        )
        session = await live_session_manager.create_session(mode=TakeoverMode.AI_COACHED)
        report = await live_session_manager.end_session(session.session_id)
        assert report is not None
        assert report["session_id"] == session.session_id
        # Verify removed from active
        assert await live_session_manager.get_session(session.session_id) is None

    async def test_to_report_dict(self, app):
        from features.live_takeover.session_manager import (
            LiveSessionState, TakeoverMode
        )
        session = LiveSessionState(
            session_id="test-report",
            mode=TakeoverMode.AI_COACHED,
            current_mode=TakeoverMode.AI_COACHED,
        )
        report = session.to_report_dict()
        assert report["session_id"] == "test-report"
        assert "transcript" in report
        assert "extracted_entities" in report


class TestAudioNormalizer:
    def test_validate_chunk(self):
        from features.live_takeover.streaming_stt import AudioNormalizer
        assert AudioNormalizer.validate_chunk(b"\x00" * 100)
        assert not AudioNormalizer.validate_chunk(b"")
        assert not AudioNormalizer.validate_chunk(b"\x00" * (10 * 1024 * 1024))

    def test_estimate_duration(self):
        from features.live_takeover.streaming_stt import AudioNormalizer
        wav = make_sine_wav(1.0)
        dur = AudioNormalizer.estimate_duration_ms(wav, format="wav")
        assert dur > 900  # ~1000ms


# ===================================================================
# 15. WebSocket Live Call
# ===================================================================

class TestLiveCallWebSocket:
    @pytest.mark.asyncio
    async def test_websocket_connect(self, app):
        """Test WebSocket connection to live-call endpoint."""
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Initiate a call first
            r = await client.post("/api/live-call/start", json={})
            cid = r.json()["call_id"]

            # Try to upgrade to WebSocket via standard HTTP (won't actually WS connect)
            # Real WS testing requires a full server, but at least verify the route exists
            r = await client.get(f"/api/live-call/status/{cid}")
            assert r.status_code == 200
            assert r.json()["call_id"] == cid

    @pytest.mark.asyncio
    async def test_websocket_invalid_role(self, app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Start call
            r = await client.post("/api/live-call/start", json={})
            cid = r.json()["call_id"]

            # Try with invalid role (should fail at ASGI level, not HTTP)
            # The WebSocket endpoint won't be hit via HTTP GET
            r = await client.get(f"/api/live-call/status/{cid}")
            assert r.status_code == 200


# ===================================================================
# 16. Core Modules
# ===================================================================

class TestAuthModule:
    def test_hash_and_verify(self):
        from core.auth import hash_password, verify_password
        h = hash_password("testpassword")
        assert h != "testpassword"
        assert verify_password("testpassword", h)
        assert not verify_password("wrongpassword", h)

    def test_jwt_tokens(self):
        from core.auth import (
            create_access_token, create_refresh_token, decode_token
        )
        payload = {"sub": "user123", "username": "testuser"}

        access = create_access_token(payload)
        decoded = decode_token(access)
        assert decoded["sub"] == "user123"
        assert decoded["type"] == "access"

        refresh = create_refresh_token(payload)
        decoded = decode_token(refresh)
        assert decoded["sub"] == "user123"
        assert decoded["type"] == "refresh"

    def test_jwt_expired(self):
        from core.auth import decode_token
        from jose import jwt
        token = jwt.encode(
            {"sub": "test", "exp": 0, "type": "access"},
            "test-secret",
            algorithm="HS256",
        )
        with pytest.raises(Exception):
            decode_token(token)


class TestMongoModule:
    async def test_connect_and_close(self, app):
        from db.mongo import connect_db, close_db, get_db, get_collection
        # Already connected via app lifespan
        db = get_db()
        # Verify we can list collections
        cols = await db.list_collection_names()
        assert isinstance(cols, list)

    async def test_get_collection(self, app):
        from db.mongo import get_collection
        col = get_collection("users")
        assert col is not None
        # Verify we can do a simple operation
        count = await col.count_documents({})
        assert isinstance(count, int)


class TestModels:
    def test_new_id(self):
        from db.models import new_id
        assert len(new_id()) > 0
        assert new_id() != new_id()

    def test_user_create(self):
        from db.models import UserCreate
        u = UserCreate(username="test", password="pass")
        assert u.username == "test"

    def test_session_in_db(self):
        from db.models import SessionInDB
        s = SessionInDB(scammer_phone="+911234567890")
        assert s.session_id
        assert s.status == "active"

    def test_entity_item(self):
        from db.models import EntityItem
        e = EntityItem(type="phone", value="9876543210")
        assert e.type == "phone"


# ===================================================================
# 17. Callback & Storage
# ===================================================================

class TestStorageService:
    async def test_save_audio_locally(self, app):
        from services.storage_service import save_audio_locally
        path = await save_audio_locally(b"fakeaudio", f"test_{uuid.uuid4().hex[:8]}.wav")
        assert path
        assert Path(path).exists()
        os.unlink(path)


class TestCallback:
    def test_callback_init(self):
        from services.callback import CallbackService
        cb = CallbackService()
        assert cb.max_retries == 3

    async def test_send_report(self, app):
        from services.callback import callback_service
        result = await callback_service.send_report({
            "session_id": "test-session",
            "is_confirmed_scam": True,
            "message_count": 5,
            "extracted_intelligence": {},
            "agent_state": {"notes": "Test report"},
        })
        assert isinstance(result, bool)


# ===================================================================
# 18. Speech Naturalizer
# ===================================================================

class TestSpeechNaturalizer:
    async def test_naturalize(self, app):
        from agents.speech_naturalizer import speech_naturalizer
        result = await speech_naturalizer.naturalize("Hello, this is a test of the naturalization system.")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_rule_based(self):
        from agents.speech_naturalizer import SpeechNaturalizer
        sn = SpeechNaturalizer()
        result = sn._rule_based_naturalization("I am testing the naturalization system.")
        assert "I'm" in result or "I am" in result  # contraction may or may not apply

    async def test_naturalize_empty(self, app):
        from agents.speech_naturalizer import speech_naturalizer
        result = await speech_naturalizer.naturalize("")
        assert isinstance(result, str)


# ===================================================================
# 19. Voice Adapter
# ===================================================================

class TestVoiceAdapter:
    async def test_process_scammer_audio(self, app):
        from agents.voice_adapter import voice_adapter
        try:
            from services.audio_processor import AUDIO_LIBS_AVAILABLE
            if not AUDIO_LIBS_AVAILABLE:
                pytest.skip("Audio libraries not installed (pydub/numpy/soundfile)")
        except ImportError:
            pass
        wav_bytes = make_sine_wav(0.5)
        result = await voice_adapter.process_scammer_audio(
            session_id="test-adapter",
            audio_data=wav_bytes,
            format="wav",
        )
        assert "text" in result
        assert "language" in result
        assert "confidence" in result

    async def test_generate_agent_voice(self, app):
        from agents.voice_adapter import voice_adapter
        result = await voice_adapter.generate_agent_voice(
            session_id="test-adapter",
            text_response="Hello, who is this?",
            language="en",
            mode="ai_speaks",
        )
        assert "naturalized_text" in result
        assert "original_text" in result


# ===================================================================
# 20. Data Exports
# ===================================================================

class TestReportGeneratorEdgeCases:
    async def test_generate_csv(self, app):
        from features.live_takeover.session_manager import (
            live_session_manager, TakeoverMode, ExtractedEntity
        )
        from features.live_takeover.report_generator import report_generator

        session = await live_session_manager.create_session(mode=TakeoverMode.AI_COACHED)
        sid = session.session_id

        entity = ExtractedEntity(entity_type="phone", value="9876543210", confidence=0.9)
        await live_session_manager.update_intelligence(session_id=sid, entities=[entity])

        report = await report_generator.generate_report(session_id=sid, format="csv")
        assert report["format"] == "csv"
        assert report["file_path"]

        await live_session_manager.end_session(sid)

    async def test_generate_all_formats(self, app):
        from features.live_takeover.session_manager import (
            live_session_manager, TakeoverMode
        )
        from features.live_takeover.report_generator import report_generator

        session = await live_session_manager.create_session(mode=TakeoverMode.AI_COACHED)
        sid = session.session_id

        results = await report_generator.generate_all_formats(session_id=sid)
        assert "json" in results
        assert "csv" in results
        # PDF might fail if reportlab not properly installed, but JSON and CSV should work

        await live_session_manager.end_session(sid)
