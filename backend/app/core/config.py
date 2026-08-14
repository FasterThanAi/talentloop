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
    GEMINI_MODEL: str = "gemini-3.5-flash"
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIMENSION: int = 768
    
    # Gmail OAuth
    GMAIL_CLIENT_ID: str | None = None
    GMAIL_CLIENT_SECRET: str | None = None
    GMAIL_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/auth/gmail/callback"
    # Sign in with Google (identity) — same OAuth client, different scopes and redirect.
    # This URI must also be registered in Google Cloud Console → Credentials.
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:5173"
    
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

    # Comma-separated in the environment, e.g.
    #   CORS_ORIGINS=https://talentloop.vercel.app,http://localhost:5173
    # In production this MUST include the exact Vercel origin, scheme included and no
    # trailing slash, or every browser request fails before it reaches a route.
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")

    @property
    def cookie_samesite(self) -> str:
        """
        Deployed, the SPA (Vercel) and the API (Render) are different sites, so a
        SameSite=lax cookie is simply never sent and every session silently dies on
        refresh. Cross-site requires SameSite=none, which browsers only accept together
        with Secure — hence the pairing below. Locally both run on the same host, so lax
        works and avoids requiring HTTPS in development.
        """
        return "none" if self.is_production else "lax"

    @property
    def cookie_secure(self) -> bool:
        return self.is_production


settings = Settings()
