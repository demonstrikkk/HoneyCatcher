from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from db.mongo import MongoDB
# Import routers (will be created in next stages)
from api import message, sessions, voice
from api import live_takeover, voice_clone, live_call, webrtc_signaling
from api import auth_routes, testing

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

# --- Rate Limiter ---
# Uses Redis if available, falls back to in-memory
try:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.REDIS_URL,
        default_limits=["200/minute"],
    )
    logger.info(f"Rate limiter using Redis: {settings.REDIS_URL}")
except Exception:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200/minute"],
    )
    logger.warning("Rate limiter using in-memory storage (Redis unavailable)")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Agentic Honey-Pot...")
    await MongoDB.connect()
    yield
    # Shutdown
    logger.info("🛑 Shutting down...")
    await MongoDB.close()

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS validation
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: Restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "details": str(exc)},
    )

# Include Routers
app.include_router(auth_routes.router, prefix="/api", tags=["Auth"])
app.include_router(message.router, prefix="/api", tags=["Message"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(voice.router, prefix="/api", tags=["Voice"])
app.include_router(live_takeover.router, prefix="/api", tags=["Live Takeover"])
app.include_router(voice_clone.router, prefix="/api", tags=["Voice Clone"])
app.include_router(live_call.router, prefix="/api", tags=["Live Call"])
app.include_router(webrtc_signaling.router, prefix="/api", tags=["WebRTC Signaling"])
app.include_router(testing.router, prefix="/api", tags=["Testing"])

# Mount Socket.IO for WebRTC signaling
app.mount("/socket.io", webrtc_signaling.sio_app)


@app.get("/health")
async def health_check():
    return {"status": "ok", "db": "connected" if MongoDB.client else "disconnected"}
