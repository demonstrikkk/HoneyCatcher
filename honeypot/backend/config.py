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
    
    # Database
    # Supporting both MONGO_URI and MONGODB_URI (user's version)
    MONGO_URI: str = Field("mongodb://localhost:27017", alias="MONGODB_URI")
    DB_NAME: str = Field("honeypot_db", alias="MONGODB_DATABASE")
    
    # AI Providers
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    
    # Callback
    GUVI_CALLBACK_URL: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

settings = Settings()
