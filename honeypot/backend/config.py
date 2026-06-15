from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # -- Core -----------------------------------------------------------------
    APP_NAME: str = "HoneyBadger API"
    API_SECRET_KEY: str = "changeme-in-production"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # -- Database -------------------------------------------------------------
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "honeypot_db"
    MONGO_URI: str = ""
    DB_NAME: str = ""

    # -- LLM ------------------------------------------------------------------
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_API_KEY: str = ""

    # -- Voice ----------------------------------------------------------------
    ELEVENLABS_API_KEY: str
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"
    ELEVENLABS_MODEL: str = "eleven_turbo_v2_5"
    ELEVENLABS_DEFAULT_VOICE: str = "Rachel"
    AUDIO_STORAGE_PATH: str = "./storage/audio"

    # -- Storage --------------------------------------------------------------
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    STORAGE_BACKEND: str = "local"

    # -- Auth -----------------------------------------------------------------
    JWT_SECRET_KEY: str = "jwt-secret-changeme"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # -- Rate Limiting --------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # -- CORS ----------------------------------------------------------------
    CORS_ORIGINS: str = "*"

    @property
    def allowed_origins(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    # -- Callback -------------------------------------------------------------
    GUVI_CALLBACK_URL: str = ""

    # -- Security -------------------------------------------------------------
    VIRUSTOTAL_API_KEY: str = ""

    # -- MinIO ----------------------------------------------------------------
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "honeybadger-audio"
    MINIO_SECURE: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
