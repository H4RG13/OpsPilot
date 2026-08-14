from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.customers import router as customers_router


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


async def test_request_validation_error_uses_standard_envelope(client: AsyncClient):
    token = await _register(client)
    response = await client.post(
        "/api/v1/customers",
        json={"email": "missing-name@customer.example"},  # "name" is required
        headers=_auth(token),
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in body["error"]
    assert "request_id" in body["error"]


async def test_unhandled_exception_returns_generic_envelope_without_leaking_details(
    client: AsyncClient, monkeypatch
):
    token = await _register(client)

    monkeypatch.setattr(
        customers_router.service,
        "list_customers",
        AsyncMock(side_effect=RuntimeError("some internal secret detail")),
    )

    # Starlette's ServerErrorMiddleware always re-raises after sending the
    # response (so an ASGI server can still log it) — httpx.ASGITransport
    # propagates that into the test by default via raise_app_exceptions.
    # This one test needs it off to inspect the graceful response the real
    # client actually receives; every other test keeps the default so
    # genuine bugs still surface as loud tracebacks, not silent 500s.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as isolated_client:
        response = await isolated_client.get("/api/v1/customers", headers=_auth(token))

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "some internal secret detail" not in response.text


async def test_responses_include_security_headers(client: AsyncClient):
    response = await client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
