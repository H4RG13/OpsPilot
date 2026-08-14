import json

from httpx import AsyncClient

from app.core.rate_limit import get_rate_limiter
from app.main import app
from app.modules.ai.dependencies import get_ai_service
from app.modules.ai.schemas import AIToolResponse, AIUsageInfo
from app.modules.ai.service import AIService

STRUCTURED_ANSWER_JSON = json.dumps(
    {
        "answer": "Revenue decreased 21.7%.",
        "insights": [],
        "recommendations": [],
        "suggested_tasks": [],
    }
)


class StubProvider:
    async def generate_with_tools(self, *, model, messages, tools, **kwargs):
        return AIToolResponse(
            content=STRUCTURED_ANSWER_JSON,
            tool_calls=[],
            model="gpt-oss-120b",
            provider="stub",
            usage=AIUsageInfo(input_tokens=10, output_tokens=5, latency_ms=10),
        )

    async def generate_text(self, *, model, messages, **kwargs):
        raise AssertionError("should not be called when no tool calls are requested")


async def _register(
    client: AsyncClient, email: str = "owner@acme.example", org: str = "Acme Commerce"
):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret123",
            "full_name": "Ada Owner",
            "organization_name": org,
        },
    )
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _override_ai_service():
    app.dependency_overrides[get_ai_service] = lambda: AIService(StubProvider())


def _clear_ai_override():
    app.dependency_overrides.pop(get_ai_service, None)


async def test_create_and_message_conversation(client: AsyncClient):
    _override_ai_service()
    try:
        token = await _register(client)

        create_response = await client.post(
            "/api/v1/ai/conversations", json={"title": "Revenue check"}, headers=_auth(token)
        )
        assert create_response.status_code == 201
        conversation_id = create_response.json()["id"]

        message_response = await client.post(
            f"/api/v1/ai/conversations/{conversation_id}/messages",
            json={"content": "Why did revenue drop?"},
            headers=_auth(token),
        )
        assert message_response.status_code == 200
        assert message_response.json()["answer"] == "Revenue decreased 21.7%."
    finally:
        _clear_ai_override()


async def test_list_conversations_scoped_to_caller(client: AsyncClient):
    _override_ai_service()
    try:
        token_a = await _register(client, email="ownera@a.example", org="Org A")
        token_b = await _register(client, email="ownerb@b.example", org="Org B")

        await client.post(
            "/api/v1/ai/conversations", json={"title": "A's chat"}, headers=_auth(token_a)
        )

        list_a = await client.get("/api/v1/ai/conversations", headers=_auth(token_a))
        list_b = await client.get("/api/v1/ai/conversations", headers=_auth(token_b))

        assert list_a.json()["total"] == 1
        assert list_b.json()["total"] == 0
    finally:
        _clear_ai_override()


async def test_cannot_message_another_users_conversation(client: AsyncClient):
    _override_ai_service()
    try:
        token_a = await _register(client, email="ownera@a.example", org="Org A")
        token_b = await _register(client, email="ownerb@b.example", org="Org B")

        create_response = await client.post(
            "/api/v1/ai/conversations", json={}, headers=_auth(token_a)
        )
        conversation_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/ai/conversations/{conversation_id}/messages",
            json={"content": "Sneaky question"},
            headers=_auth(token_b),
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"
    finally:
        _clear_ai_override()


class DenyingRateLimiter:
    async def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        return False


async def test_message_rate_limited_returns_429(client: AsyncClient):
    _override_ai_service()
    app.dependency_overrides[get_rate_limiter] = lambda: DenyingRateLimiter()
    try:
        token = await _register(client)
        create_response = await client.post(
            "/api/v1/ai/conversations", json={}, headers=_auth(token)
        )
        conversation_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/ai/conversations/{conversation_id}/messages",
            json={"content": "Why did revenue drop?"},
            headers=_auth(token),
        )
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "RATE_LIMITED"
    finally:
        _clear_ai_override()
        app.dependency_overrides.pop(get_rate_limiter, None)
