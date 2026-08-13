from httpx import AsyncClient

from app.main import app
from app.modules.reports.dependencies import get_report_dispatcher


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


def _override_dispatcher(spy: list):
    app.dependency_overrides[get_report_dispatcher] = lambda: spy.append


def _clear_dispatcher_override():
    app.dependency_overrides.pop(get_report_dispatcher, None)


async def test_generate_report_creates_queued_report_and_dispatches(client: AsyncClient):
    dispatched_ids: list = []
    _override_dispatcher(dispatched_ids)
    try:
        token = await _register(client)
        response = await client.post("/api/v1/reports/generate", headers=_auth(token))
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "queued"
        assert len(dispatched_ids) == 1
        assert str(dispatched_ids[0]) == body["id"]
    finally:
        _clear_dispatcher_override()


async def test_list_reports_scoped_to_organization(client: AsyncClient):
    dispatched_ids: list = []
    _override_dispatcher(dispatched_ids)
    try:
        token_a = await _register(client, email="ownera@a.example", org="Org A")
        token_b = await _register(client, email="ownerb@b.example", org="Org B")

        await client.post("/api/v1/reports/generate", headers=_auth(token_a))

        list_a = await client.get("/api/v1/reports", headers=_auth(token_a))
        list_b = await client.get("/api/v1/reports", headers=_auth(token_b))

        assert list_a.json()["total"] == 1
        assert list_b.json()["total"] == 0
    finally:
        _clear_dispatcher_override()
