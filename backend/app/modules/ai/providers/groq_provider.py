import time
from typing import Any

import httpx

from app.modules.ai.providers.base import (
    AIProvider,
    PermanentProviderError,
    TransientProviderError,
)
from app.modules.ai.schemas import AITextResponse, AIToolCall, AIToolResponse, AIUsageInfo

GROQ_API_BASE_URL = "https://api.groq.com/openai/v1"

# Transient: worth retrying or falling back to another model. Everything else
# (bad request, auth, unknown model) is permanent and fails fast instead.
_TRANSIENT_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


class GroqProvider(AIProvider):
    """Groq's chat completions API is OpenAI-compatible; this speaks that wire format directly."""

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float,
        http_client: httpx.AsyncClient | None = None,
    ):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client or httpx.AsyncClient(base_url=GROQ_API_BASE_URL)

    async def generate_text(
        self, *, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> AITextResponse:
        payload = await self._chat_completion(model=model, messages=messages, **kwargs)
        choice = payload["choices"][0]["message"]
        return self._to_text_response(payload, model, choice.get("content") or "")

    async def generate_structured(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
        **kwargs: Any,
    ) -> AITextResponse:
        payload = await self._chat_completion(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            **kwargs,
        )
        choice = payload["choices"][0]["message"]
        return self._to_text_response(payload, model, choice.get("content") or "")

    async def generate_with_tools(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AIToolResponse:
        payload = await self._chat_completion(model=model, messages=messages, tools=tools, **kwargs)
        message = payload["choices"][0]["message"]

        tool_calls = [
            AIToolCall(
                id=call["id"],
                name=call["function"]["name"],
                arguments=call["function"].get("arguments", {}),
            )
            for call in message.get("tool_calls") or []
        ]

        usage = self._extract_usage(payload)
        return AIToolResponse(
            content=message.get("content"),
            tool_calls=tool_calls,
            model=payload.get("model", model),
            provider="groq",
            usage=usage,
        )

    async def generate_vision(
        self, *, model: str, messages: list[dict[str, str]], image_url: str, **kwargs: Any
    ) -> AITextResponse:
        vision_messages = [*messages, {"role": "user", "content": image_url}]
        payload = await self._chat_completion(model=model, messages=vision_messages, **kwargs)
        choice = payload["choices"][0]["message"]
        return self._to_text_response(payload, model, choice.get("content") or "")

    async def _chat_completion(
        self, *, model: str, messages: list[dict[str, str]], **kwargs: Any
    ) -> dict[str, Any]:
        start = time.monotonic()
        try:
            response = await self._http_client.post(
                "/chat/completions",
                json={"model": model, "messages": messages, **kwargs},
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise TransientProviderError(f"Groq request timed out for model '{model}'.") from exc
        except httpx.HTTPError as exc:
            raise TransientProviderError(f"Groq request failed for model '{model}': {exc}") from exc

        latency_ms = int((time.monotonic() - start) * 1000)

        if response.status_code >= 400:
            if response.status_code in _TRANSIENT_STATUS_CODES:
                raise TransientProviderError(
                    f"Groq returned {response.status_code} for model '{model}'."
                )
            raise PermanentProviderError(
                f"Groq returned {response.status_code} for model '{model}': {response.text}"
            )

        payload = response.json()
        payload["_latency_ms"] = latency_ms
        return payload

    @staticmethod
    def _extract_usage(payload: dict[str, Any]) -> AIUsageInfo:
        usage = payload.get("usage") or {}
        return AIUsageInfo(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_ms=payload.get("_latency_ms", 0),
        )

    def _to_text_response(
        self, payload: dict[str, Any], model: str, content: str
    ) -> AITextResponse:
        return AITextResponse(
            content=content,
            model=payload.get("model", model),
            provider="groq",
            usage=self._extract_usage(payload),
        )
