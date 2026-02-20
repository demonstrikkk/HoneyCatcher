# HoneyBadger - Installation & Setup

## Quick Start (Windows)

### Option 1: Automated Start
```bash
# Run the complete system startup script
START_ALL.bat
```

This will:
1. Start backend server (port 8000)
2. Start frontend server (port 5173)
3. Optionally start ngrok tunnels
4. Open browser automatically

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd honeypot/backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd honeypot/frontend
npm install
npm run dev
```

**Terminal 3 - ngrok (Optional):**
```bash
ngrok start --all
```

## Environment Setup

### Backend (.env)
Create `honeypot/backend/.env`:
```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=honeypot_db

# API Keys (Optional - Free features work without them)
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
ELEVENLABS_API_KEY=optional_key  # Free voices work without this!

# ElevenLabs Settings
ELEVENLABS_DEFAULT_VOICE=Rachel
ELEVENLABS_MODEL=eleven_turbo_v2_5

# JWT
JWT_SECRET_KEY=your-secret-key-here

# Audio Storage
AUDIO_STORAGE_PATH=./storage/audio
```

### Frontend (.env)
Create `honeypot/frontend/.env`:
```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_BASE_URL=ws://localhost:8000/api
VITE_SOCKET_URL=http://localhost:8000
```

## ngrok Configuration (Optional)

### Copy ngrok.yml
Copy `ngrok.yml` to:
- **Windows:** `C:\Users\<username>\.ngrok2\ngrok.yml`
- **Linux/Mac:** `~/.ngrok2/ngrok.yml`

Add your ngrok authtoken to the file.

### Start Multiple Tunnels
```bash
ngrok start --all
```

Or use the Windows script:
```bash
start-ngrok.bat
```

## Verify Installation

### Check Backend
```bash
curl http://localhost:8000/health
# Should return: {"status": "ok", "db": "connected"}
```

### Check Frontend
Open browser: http://localhost:5173

### Check API Docs
Open browser: http://localhost:8000/docs

## System Requirements

- **Python:** 3.9 or higher
- **Node.js:** 18 or higher
- **MongoDB:** 5.0 or higher (optional - defaults to localhost)
- **ngrok:** Latest version (optional - for external access)

## Port Usage

| Service | Port | URL |
|---------|------|-----|
| Backend | 8000 | http://localhost:8000 |
| Frontend | 5173 | http://localhost:5173 |
| MongoDB | 27017 | mongodb://localhost:27017 |

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Install missing dependencies
cd honeypot/backend
pip install -r requirements.txt --upgrade
```

### Frontend won't start
```bash
# Check if port 5173 is in use
netstat -ano | findstr :5173

# Reinstall dependencies
cd honeypot/frontend
rm -rf node_modules package-lock.json
npm install
```

### MongoDB connection failed
```bash
# Start MongoDB service (Windows)
net start MongoDB

# Or install MongoDB
# Download from: https://www.mongodb.com/try/download/community
```

### ngrok tunnels not working
```bash
# Verify ngrok is installed
ngrok version

# Check ngrok.yml location
dir %USERPROFILE%\.ngrok2\ngrok.yml

# Test single tunnel
ngrok http 8000
```

## Next Steps

Once everything is running:

1. **Create an account** at http://localhost:5173
2. **Start a live call** from the dashboard
3. **Test audio** from both operator and scammer sides
4. **Verify AI voice** plays using ElevenLabs
5. **Check real-time transcription** appears

## Features Ready to Use

✅ Live two-way voice calls  
✅ Real-time transcription  
✅ AI coaching with natural voices (9 free voices!)  
✅ Intelligence extraction  
✅ Connection auto-recovery  
✅ Echo cancellation & noise suppression  
✅ WebRTC with TURN server support  
✅ Mobile browser compatibility  

## Documentation

- **Complete Guide:** [LIVE_CALL_COMPLETE_GUIDE.md](LIVE_CALL_COMPLETE_GUIDE.md)
- **API Reference:** http://localhost:8000/docs
- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)

---

**Ready to catch scammers!** 🎯🦡
