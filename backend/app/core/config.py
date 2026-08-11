import logging
import os
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("talentloop.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./talentloop.db"
    
    # Gemini AI
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIMENSION: int = 768
    
    # Gmail OAuth
    GMAIL_CLIENT_ID: str | None = None
    GMAIL_CLIENT_SECRET: str | None = None
    GMAIL_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/auth/gmail/callback"
    
    # Security
    JWT_SECRET: str = "talentloop-super-secret-jwt-key-2026-very-secure"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_KEY: str | None = None
    
    # Feature Flags
    HUNTER_ENABLED: bool = False
    RIZEOS_ENABLED: bool = False
    CREDENTIAL_ANCHOR_ENABLED: bool = False
    
    # RAG / Sourcing defaults
    RESPONSE_MIN_RELEVANCE: float = 0.65
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]


settings = Settings()
