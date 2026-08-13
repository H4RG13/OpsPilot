import httpx
import pytest

from app.modules.ai.providers.base import PermanentProviderError, TransientProviderError
from app.modules.ai.providers.groq_provider import GroqProvider


def _client_with_handler(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, base_url="https://api.groq.com/openai/v1")


async def test_generate_text_parses_content_and_usage():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "model": "gpt-oss-20b",
                "choices": [{"message": {"role": "assistant", "content": "hi there"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            },
        )

    provider = GroqProvider(
        api_key="test-key", timeout_seconds=5, http_client=_client_with_handler(handler)
    )
    response = await provider.generate_text(
        model="gpt-oss-20b", messages=[{"role": "user", "content": "hi"}]
    )

    assert response.content == "hi there"
    assert response.provider == "groq"
    assert response.usage.input_tokens == 12
    assert response.usage.output_tokens == 4
    assert response.usage.latency_ms >= 0


async def test_rate_limit_raises_transient_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"})

    provider = GroqProvider(
        api_key="test-key", timeout_seconds=5, http_client=_client_with_handler(handler)
    )
    with pytest.raises(TransientProviderError):
        await provider.generate_text(model="gpt-oss-20b", messages=[])


async def test_bad_request_raises_permanent_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid model"})

    provider = GroqProvider(
        api_key="test-key", timeout_seconds=5, http_client=_client_with_handler(handler)
    )
    with pytest.raises(PermanentProviderError):
        await provider.generate_text(model="unknown-model", messages=[])


async def test_timeout_raises_transient_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out")

    provider = GroqProvider(
        api_key="test-key", timeout_seconds=5, http_client=_client_with_handler(handler)
    )
    with pytest.raises(TransientProviderError):
        await provider.generate_text(model="gpt-oss-20b", messages=[])


async def test_generate_with_tools_parses_tool_calls():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "gpt-oss-120b",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "function": {
                                        "name": "get_revenue_summary",
                                        "arguments": {"start_date": "2026-01-01"},
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 8},
            },
        )

    provider = GroqProvider(
        api_key="test-key", timeout_seconds=5, http_client=_client_with_handler(handler)
    )
    response = await provider.generate_with_tools(
        model="gpt-oss-120b", messages=[{"role": "user", "content": "why"}], tools=[]
    )

    assert response.tool_calls[0].name == "get_revenue_summary"
    assert response.tool_calls[0].arguments == {"start_date": "2026-01-01"}
