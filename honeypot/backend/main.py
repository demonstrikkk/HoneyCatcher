from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings
from db.mongo import MongoDB
# Import routers (will be created in next stages)
from api import message, sessions, voice

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

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
app.include_router(message.router, prefix="/api", tags=["Message"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(voice.router, prefix="/api", tags=["Voice"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "db": "connected" if MongoDB.client else "disconnected"}
