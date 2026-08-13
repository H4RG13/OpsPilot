from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "ai-operations-copilot"
    secret_key: str = Field(default="change-me")

    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/ai_ops"
    redis_url: str = "redis://redis:6379/0"

    groq_api_key: str = ""
    openai_api_key: str = ""

    ai_default_model: str = "gpt-oss-20b"
    ai_reasoning_model: str = "gpt-oss-120b"
    ai_vision_model: str = "qwen-3.6-27b"

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    frontend_url: str = "http://localhost:5173"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _require_strong_secret_in_production(self) -> "Settings":
        if self.is_production and (self.secret_key == "change-me" or len(self.secret_key) < 32):
            raise ValueError(
                "SECRET_KEY must be set to a strong, unique value (>=32 chars) in production."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
