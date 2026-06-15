import logging
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from core.lifecycle import lifespan

# Routes
from api.auth_routes      import router as auth_router
from api.sessions         import router as sessions_router
from api.message          import router as message_router
from api.voice            import router as voice_router
from api.live_call        import router as live_call_router
from api.live_takeover    import router as live_takeover_router
from api.voice_clone      import router as voice_clone_router
from api.elevenlabs_routes import router as elevenlabs_router
from api.testing          import router as testing_router
from api.sms_evidence     import router as sms_evidence_router
from api.agora_routes     import router as agora_router
from api.webrtc_signaling import sio

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

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

# Register REST/WS routers
for r in [
    auth_router, sessions_router, message_router, voice_router,
    live_call_router, live_takeover_router, voice_clone_router,
    elevenlabs_router, testing_router, sms_evidence_router, agora_router,
]:
    app.include_router(r)

# Mount Socket.IO for WebRTC signaling
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


@app.get("/health")
async def health():
    return {"status": "ok"}
