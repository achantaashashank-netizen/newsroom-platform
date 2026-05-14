from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    SECRET_KEY: str = "change-me-in-production"
    FERNET_SECRET_KEY: str = ""
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://newsroom:newsroom_secret@localhost:5433/newsroom_db"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://newsroom:newsroom_secret@localhost:5433/newsroom_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # OpenAI (DALL-E / gpt-image-1)
    OPENAI_API_KEY: str = ""

    # Hugging Face (FLUX.1 image generation — free tier)
    HF_TOKEN: str = ""

    # News Discovery
    NEWSAPI_KEY: str = ""

    # Media
    GOOGLE_CSE_API_KEY: str = ""
    GOOGLE_CSE_ID: str = ""
    UNSPLASH_ACCESS_KEY: str = ""
    MEDIA_DIR: str = "/app/media"

    # Meta Graph API
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_REDIRECT_URI: str = "http://localhost:8080/api/social-accounts/meta/callback"

    # Verification thresholds
    CONFIDENCE_LOW_THRESHOLD: float = 0.35
    CONFIDENCE_HIGH_THRESHOLD: float = 0.65

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # LangGraph thread config
    LANGGRAPH_RECURSION_LIMIT: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
