# HoneyBadger Testing Guide

## Complete Testing Workflow for Audio Transcription & Intelligence Extraction

This guide provides step-by-step instructions for testing all major features of the HoneyBadger honeypot system.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Backend Setup & Verification](#backend-setup--verification)
3. [VirusTotal Integration Testing](#virustotal-integration-testing)
4. [Audio Transcription Testing](#audio-transcription-testing)
5. [Intelligence Extraction Testing](#intelligence-extraction-testing)
6. [Debugging Guide](#debugging-guide)
7. [Common Issues & Solutions](#common-issues--solutions)

---

## Prerequisites

### Environment Variables

Ensure these are set in `backend/.env`:

```bash
# Required
OPENAI_API_KEY=sk-...
VIRUSTOTAL_API_KEY=your_virustotal_api_key_here

# Optional but recommended
MONGODB_URI=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379
```

### API Key Setup

1. **VirusTotal API Key**: Get one for free at https://www.virustotal.com/gui/my-apikey
   - Free tier: 4 requests/minute, 500/day
   - Set in `.env` as `VIRUSTOTAL_API_KEY`

2. **OpenAI API Key**: Required for transcription and AI coaching
   - Get from https://platform.openai.com/api-keys
   - Set in `.env` as `OPENAI_API_KEY`

---

## Backend Setup & Verification

### 1. Start the Backend

```bash
cd honeypot/backend
python main.py
```

**Expected Output:**
```
🚀 Starting Agentic Honey-Pot...
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Verify Health Endpoint

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "db": "connected"
}
```

### 3. Check VirusTotal Configuration

```bash
curl http://localhost:8000/api/test-virustotal/info
```

**Expected Response:**
```json
{
  "virustotal_configured": true,
  "api_key_set": true,
  "test_urls": {
    "malicious": [...],
    "safe": [...]
  }
}
```

⚠️ If `virustotal_configured` is `false`, check your `.env` file.

---

## VirusTotal Integration Testing

### Method 1: API Endpoint (Direct)

```bash
curl -X POST http://localhost:8000/api/test-virustotal \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "http://malware.testing.google.test/testing/malware/",
      "https://www.google.com"
    ]
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "total_urls": 2,
  "results": [
    {
      "url": "http://malware.testing.google.test/testing/malware/",
      "is_safe": false,
      "risk_score": 0.85,
      "summary": "⚠️ MALICIOUS - Risk: 85.0%",
      "findings": [
        "Google Safebrowsing: malware",
        "Fortinet: Malware",
        "Kaspersky: Malicious"
      ]
    },
    {
      "url": "https://www.google.com",
      "is_safe": true,
      "risk_score": 0.0,
      "summary": "✅ SAFE - Risk: 0.0%"
    }
  ]
}
```

### Method 2: UI Button (Recommended)

1. **Open Frontend:** http://localhost:5173
2. **Navigate to any session view** (e.g., `/session/abc123`)
3. **Click "Test VirusTotal"** button in the Intelligence Panel
4. **Observe results** displayed in purple panel below button

**What You'll See:**
- 🟢 Green = Safe URL (risk < 0.3)
- 🔴 Red = Malicious URL (risk ≥ 0.3)
- Risk score percentage
- Top 3 scanner findings

### Test URLs Reference

| URL | Expected Result | Description |
|-----|----------------|-------------|
| `http://malware.testing.google.test/testing/malware/` | ⚠️ MALICIOUS | Google Safe Browsing test URL |
| `https://www.eicar.org/download/eicar.com.txt` | ⚠️ MALICIOUS | EICAR anti-malware test file |
| `http://testsafebrowsing.appspot.com/s/malware.html` | ⚠️ MALICIOUS | Google test page |
| `https://www.google.com` | ✅ SAFE | Google homepage |
| `https://www.github.com` | ✅ SAFE | GitHub homepage |

### Backend Logs to Watch

```
🔗 Scanning 2 URLs with VirusTotal...
🔍 Starting URL scan for 2 URLs: ['http://malware...', 'https://www.google.com']
🔎 URL Scan Result: http://malware... - MALICIOUS (risk: 0.85)
📤 Sent URL scan result to operator for http://malware...
✅ Completed scanning 2 URLs
```

---

## Audio Transcription Testing

### Setup

1. **Start Backend:** `python main.py` (see above)
2. **Start Frontend:** `cd frontend && npm run dev`
3. **Open Browser:** http://localhost:5173
4. **Allow microphone permissions** when prompted

### Testing Steps

#### 1. Start a Live Call

1. Navigate to **Playground** or **Live Call** page
2. Click **"Start Call"** or **"Connect"**
3. Wait for WebRTC connection (green indicator)

#### 2. Enable Audio (Critical!)

⚠️ **IMPORTANT:** Audio won't play without this step due to browser autoplay policies.

1. Look for **yellow banner** at top: "Enable Audio"
2. **Click the "Enable Audio" button**
3. Verify banner disappears

**If button not clickable:**
- Check browser console for errors
- Try clicking multiple times
- Ensure peer connection is established first

#### 3. Speak and Observe

1. **Speak clearly** into your microphone
2. **Speak loudly** (VAD filters quiet audio as silence)
3. **Watch for:**
   - Audio chunks being sent (console logs)
   - Transcription appearing in UI within 2-3 seconds
   - Intelligence being extracted if scam keywords used

### Expected Console Logs

**Frontend (Browser Console):**
```
🎤 Audio chunk captured: 41984 bytes
📤 Sending audio chunk: speaker=operator, bytes=41984
✅ Audio chunk sent successfully
```

**Backend (Terminal):**
```
📨 Received audio chunk: speaker=operator, room_id=abc123, size=41984
🔊 Processing transcription: speaker=operator, duration=2.0s
📝 Transcription result: "Hello, this is a test message"
📤 Emitted transcription to room abc123
💾 Saved transcript to database
```

### Expected UI Behavior

1. **Transcription appears** in chat panel as speech bubble
2. **Speaker label** shows "Operator" or "Scammer"
3. **Timestamp** shows when spoken
4. **Intelligence extracts** if scam keywords detected

### Troubleshooting Audio Issues

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| No audio chunks sent | Mic permission denied | Check browser permissions |
| Chunks sent but "Skipping silent chunk" | Volume too low | Speak louder or adjust mic gain |
| No transcription appearing | OpenAI API key missing | Check `.env` file |
| "Enable Audio" button stuck | Autoplay blocked | Click button, check for errors |
| Audio chunks very small (<5KB) | Silence detected | Speak more loudly |

---

## Intelligence Extraction Testing

### Test Scam Keywords

Speak these phrases to trigger intelligence extraction:

#### High Severity (Threat Level +0.8):
- "Your account has been **blocked**"
- "There is an **arrest warrant** in your name"
- "Police will **arrest** you tomorrow"
- "This is **money laundering** investigation"
- "FIR has been **filed** against you"

#### Medium Severity (Threat Level +0.5):
- "Please **verify your KYC**"
- "Claim your **refund** now"
- "You have won a **lottery**"
- "Submit your **documents** immediately"

#### Low Severity (Threat Level +0.3):
- "Your **bank account** needs attention"
- "Enter the **OTP** you received"
- "Share your **password**"

### Test Entity Extraction

Speak these to extract specific entities:

| Entity Type | Example Phrase | Expected Extraction |
|-------------|---------------|---------------------|
| Phone Number | "Call me at 9876543210" | Phone: 9876543210 |
| Bank Account | "Transfer to 12345678901234" | Bank: 12345678901234 |
| UPI ID | "Pay to john@paytm" | UPI: john@paytm |
| URL | "Visit malware.testing.google.test" | URL: malware... |
| IFSC Code | "Use SBIN0001234" | IFSC: SBIN0001234 |
| Email | "Send to scammer@evil.com" | Email: scammer@evil.com |

### Expected Intelligence Panel

After speaking scam phrases, the Intelligence Panel should show:

```
Bank Accounts
┌─────────────────────┐
│ 12345678901234      │
└─────────────────────┘

Phone Numbers
┌─────────────────────┐
│ 9876543210          │
└─────────────────────┘

Phishing Links
┌─────────────────────┐
│ malware.testing...  │
└─────────────────────┘

Triggers (Scam Keywords)
┌─────────────────────┐
│ blocked             │
│ verify              │
│ arrest warrant      │
└─────────────────────┘
```

### Expected Backend Logs

```
🧠 Extracting intelligence from: 'Your account has been blocked...'
✅ Extracted 3 entities, threat level: 0.80
🎯 Detected tactics: fear, authority
🔗 Scanning 1 URLs with VirusTotal...
📤 Sent intelligence update to operator
💾 Saved intelligence to database
```

### URL Scanning in Intelligence

When a URL is mentioned:

1. **Extracted** as entity
2. **Sent to VirusTotal** automatically
3. **Results emitted** to operator via Socket.IO
4. **Displayed** in Intelligence Panel with risk score

**Frontend will receive:**
```javascript
socket.on('url_scan_result', (data) => {
  console.log('🔎 URL Scan:', data.url, data.is_safe ? 'SAFE' : 'MALICIOUS');
});
```

---

## Debugging Guide

### Enable Comprehensive Logging

All major functions now have extensive logging with emojis for easy scanning:

```
🚀 = Startup/Initialization
📨 = Receiving data
📤 = Sending data
🔊 = Audio processing
📝 = Transcription
🧠 = Intelligence extraction
🔗 = URL detected
🔍 = URL scanning started
🔎 = URL scan result
✅ = Success
❌ = Error
⚠️ = Warning
```

### Check Logs Step-by-Step

#### 1. Audio Chunk Flow

**Frontend Console:**
```javascript
🎤 Audio chunk captured: 41984 bytes
📤 Sending audio chunk: speaker=operator, bytes=41984
```

**Backend Terminal:**
```python
📨 Received audio chunk: speaker=operator, room_id=abc123, size=41984
🔊 Processing transcription: speaker=operator, duration=2.0s
```

#### 2. Transcription Flow

```python
📝 Transcription result: "Your account has been blocked"
📤 Emitted transcription to room abc123
💾 Saved transcript to database
```

#### 3. Intelligence Flow

```python
🧠 Extracting intelligence from: 'Your account has been blocked'
✅ Extracted 1 entities, threat level: 0.80
🎯 Detected tactics: fear, authority
📤 Sent intelligence update to operator
```

#### 4. URL Scanning Flow

```python
🔗 Scanning 1 URLs with VirusTotal...
🔍 Starting URL scan for 1 URLs: ['http://malware...']
🔎 URL Scan Result: http://malware... - MALICIOUS (risk: 0.85)
📤 Sent URL scan result to operator
✅ Completed scanning 1 URLs
```

### Debug Commands

**Check if Socket.IO is receiving:**
```javascript
// Browser console
socket.on('connect', () => console.log('✅ Socket connected'));
socket.on('transcription_result', (d) => console.log('📝 Transcription:', d));
socket.on('intelligence_update', (d) => console.log('🧠 Intelligence:', d));
socket.on('url_scan_result', (d) => console.log('🔎 URL Scan:', d));
```

**Check backend transcription service:**
```bash
# In Python
from services.stt_service import StreamingTranscriber
transcriber = StreamingTranscriber()
result = transcriber.transcribe_chunk(audio_bytes)
print(result)
```

---

## Common Issues & Solutions

### Issue: "Enable Audio" Button Not Clickable

**Symptoms:**
- Button visible but clicks don't work
- No console errors

**Solutions:**
1. Ensure peer connection established (green indicator)
2. Check CSS z-index isn't blocking clicks
3. Try clicking multiple times (autoplay can be finicky)
4. Check browser console for pointer-events CSS

**Code to check:**
```javascript
// In browser console
const btn = document.querySelector('button:has-text("Enable Audio")');
console.log('Button:', btn);
console.log('Pointer events:', window.getComputedStyle(btn).pointerEvents);
console.log('Z-index:', window.getComputedStyle(btn).zIndex);
```

---

### Issue: Audio Chunks Sent But Not Transcribed

**Symptoms:**
- Console shows "📤 Sending audio chunk"
- Backend shows "Skipping silent chunk"

**Root Cause:** Voice Activity Detection (VAD) filtering silence

**Solutions:**
1. **Speak louder** - VAD is sensitive to volume
2. **Check mic volume** in system settings
3. **Disable VAD** (for testing only):
   ```python
   # In audio_processor.py
   def is_voice_detected(self, audio_data):
       return True  # Disable VAD temporarily
   ```

---

### Issue: No Intelligence Extracted

**Symptoms:**
- Transcription appears
- Intelligence panel empty

**Solutions:**
1. Use **exact scam keywords** from list above
2. Check speaker label (intelligence only extracts from "scammer")
3. Verify regex patterns in `intelligence_pipeline.py`

---

### Issue: VirusTotal Test Fails

**Symptoms:**
- Test button shows error
- "API key not configured"

**Solutions:**
1. Check `.env` file has `VIRUSTOTAL_API_KEY=...`
2. Restart backend after adding key
3. Verify key at `/api/test-virustotal/info`
4. Check rate limits (4/min free tier)

**Test API key manually:**
```bash
curl -H "x-apikey: YOUR_API_KEY" \
  https://www.virustotal.com/api/v3/urls/google.com
```

---

### Issue: WebRTC Connection Fails

**Symptoms:**
- Peer never connects
- No audio chunks sent

**Solutions:**
1. Check Socket.IO connection in console
2. Verify backend is running on port 8000
3. Check CORS settings allow frontend origin
4. Try different browser (Chrome recommended)

---

## Advanced Testing

### Load Testing

Test multiple concurrent calls:

```bash
# Terminal 1: Start backend
python main.py

# Terminal 2-5: Simulate multiple clients
for i in {1..4}; do
  curl -X POST http://localhost:8000/api/webrtc/create-room \
    -H "Content-Type: application/json" \
    -d '{"room_type": "operator"}' &
done
```

### Memory Testing

Monitor memory usage during long calls:

```bash
# Watch backend memory
watch -n 1 'ps aux | grep "python main.py" | grep -v grep | awk "{print \$4}"'
```

### Database Verification

Check if transcripts are being saved:

```javascript
// MongoDB shell
use honeypot
db.live_calls.find().sort({_id: -1}).limit(1).pretty()
```

---

## Success Criteria Checklist

Use this checklist to verify all systems are working:

- [ ] Backend starts without errors
- [ ] `/health` endpoint returns `connected`
- [ ] VirusTotal API key configured
- [ ] VirusTotal test endpoint returns results
- [ ] UI Test VirusTotal button works
- [ ] Frontend connects to backend
- [ ] WebRTC peer connection established
- [ ] "Enable Audio" button appears and works
- [ ] Audio chunks are sent (>5KB size)
- [ ] Transcriptions appear in UI within 3s
- [ ] Scam keywords trigger intelligence extraction
- [ ] Intelligence panel shows extracted entities
- [ ] URLs automatically scanned with VirusTotal
- [ ] URL scan results appear in Intelligence Panel
- [ ] Threat level increases with severity keywords
- [ ] Tactics detected (fear, authority, etc.)
- [ ] Database saves transcripts and intelligence
- [ ] No memory leaks during extended testing

---

## Getting Help

If you encounter issues not covered here:

1. **Check backend logs** for error stack traces
2. **Check browser console** for frontend errors
3. **Enable debug mode:** Set `LOG_LEVEL=DEBUG` in `.env`
4. **Test components individually:**
   - Transcription: `python backend/test_components.py`
   - VirusTotal: `curl /api/test-virustotal/info`
   - Socket.IO: Check connection in browser DevTools > Network > WS

---

## Appendix: Sample Test Session

Complete end-to-end test transcript:

```
1. Start backend: python main.py
2. Start frontend: npm run dev
3. Open http://localhost:5173
4. Navigate to /playground
5. Click "Start Call" → WebRTC connects
6. Click "Enable Audio" → Banner disappears
7. Speak: "Your bank account has been blocked due to suspicious activity"
8. Wait 2-3 seconds
9. Verify transcription appears
10. Verify "blocked" appears in Triggers
11. Verify threat level increases
12. Speak: "Visit malware.testing.google.test/testing/malware"
13. Wait for VirusTotal scan (3-5 seconds)
14. Verify URL appears in Phishing Links with MALICIOUS label
15. Click "Test VirusTotal" button
16. Verify test results show malicious URL detected
17. Click "End Call"
18. Verify session saved with all data
```

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**Tested On:** Python 3.11, Node 20, Chrome 120
