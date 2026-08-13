from typing import Any, Protocol

from app.modules.ai.schemas import AITextResponse, AIToolResponse


class ProviderError(Exception):
    """Base class for AI provider failures."""


class TransientProviderError(ProviderError):
    """Retryable failure: timeout, rate limit, 5xx from the provider."""


class PermanentProviderError(ProviderError):
    """Non-retryable failure: invalid request, auth failure, unsupported model."""


class AIProvider(Protocol):
    """Vendor-agnostic interface. Depend on this, never on a provider SDK directly."""

    async def generate_text(
        self, *, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> AITextResponse: ...

    async def generate_structured(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
        **kwargs: Any,
    ) -> AITextResponse: ...

    async def generate_with_tools(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AIToolResponse: ...

    async def generate_vision(
        self, *, model: str, messages: list[dict[str, str]], image_url: str, **kwargs: Any
    ) -> AITextResponse: ...
