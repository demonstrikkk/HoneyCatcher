import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False
    )

    # App
    APP_NAME: str = "Agentic Honey-Pot"
    DEBUG: bool = True
    API_SECRET_KEY: str = "unsafe-secret-key-change-me"
    CORS_ORIGINS: str = "*"  # Comma-separated list of allowed origins for production
    
    # Database
    # Supporting both MONGO_URI and MONGODB_URI (user's version)
    MONGO_URI: str = Field("mongodb://localhost:27017", alias="MONGODB_URI")
    DB_NAME: str = Field("honeypot_db", alias="MONGODB_DATABASE")
    
    # AI Providers
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    
    # Callback
    GUVI_CALLBACK_URL: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "change-me-to-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Live Takeover - ElevenLabs Voice Cloning
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_MODEL: str = "eleven_turbo_v2_5"
    ELEVENLABS_DEFAULT_VOICE: str = "Rachel"  # Default voice for AI responses
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice ID
    
    # Audio Storage
    AUDIO_STORAGE_PATH: str = "./storage/audio"
    
    # URL Scanning
    VIRUSTOTAL_API_KEY: str = ""
    
    # MinIO / S3-compatible Object Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "honeybadger-audio"
    MINIO_SECURE: bool = False
    
    # Redis (for rate limiting)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Cloudinary (cloud storage for audio/reports)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

settings = Settings()
