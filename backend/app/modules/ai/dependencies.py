from functools import lru_cache

from app.core.config import settings
from app.modules.ai.providers.groq_provider import GroqProvider
from app.modules.ai.service import AIService


@lru_cache
def get_ai_service() -> AIService:
    provider = GroqProvider(
        api_key=settings.groq_api_key, timeout_seconds=settings.ai_request_timeout_seconds
    )
    return AIService(provider)
