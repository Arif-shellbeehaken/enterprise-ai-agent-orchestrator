"""
Application configuration using Pydantic BaseSettings.
Loads from environment variables or .env file.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Enterprise AI Agent Orchestrator"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", description="development | staging | production")
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32",
        description="JWT signing key",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    # Database (PostgreSQL + pgvector ready)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://orchestrator:orchestrator@localhost:5432/orchestrator",
        description="Async SQLAlchemy connection string",
    )
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # LLM / LiteLLM gateway
    LITELLM_MODEL: str = "gemini/gemini-2.0-flash"
    GOOGLE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEFAULT_TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 4096

    # Human-in-the-Loop
    APPROVAL_THRESHOLD_USD: float = 100.00
    HITL_WEBHOOK_URL: Optional[str] = None  # Frontend notification endpoint

    # PII / Presidio
    PII_LANGUAGE: str = "en"
    PII_ENTITIES: List[str] = Field(
        default_factory=lambda: [
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "US_SSN",
            "PERSON",
            "API_KEY",
        ]
    )

    # Observability
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "http://localhost:3000"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def validate_for_production(s: Settings) -> None:
    """Fail fast if production is misconfigured."""
    if s.ENVIRONMENT != "production":
        return
    weak = (
        not s.SECRET_KEY
        or s.SECRET_KEY.startswith("change-me")
        or len(s.SECRET_KEY) < 32
    )
    if weak:
        raise RuntimeError(
            "SECRET_KEY must be a strong random value (>=32 chars) in production. "
            "Generate with: openssl rand -hex 32"
        )
    if s.DEBUG:
        raise RuntimeError("DEBUG must be False in production")
    if any("localhost" in o for o in s.CORS_ORIGINS):
        import logging
        logging.getLogger(__name__).warning(
            "CORS_ORIGINS contains localhost in production – verify this is intentional"
        )

