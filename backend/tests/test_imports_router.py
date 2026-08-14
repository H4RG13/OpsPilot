from httpx import AsyncClient

from app.core.security import hash_password
from app.main import app
from app.modules.imports.dependencies import get_import_dispatcher
from app.modules.organizations.models import OrganizationMember
from app.modules.users.models import User
from app.shared.permissions import Role


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
    app.dependency_overrides[get_import_dispatcher] = lambda: spy.append


def _clear_dispatcher_override():
    app.dependency_overrides.pop(get_import_dispatcher, None)


async def test_upload_csv_creates_queued_job_and_dispatches(client: AsyncClient):
    dispatched: list = []
    _override_dispatcher(dispatched)
    try:
        token = await _register(client)
        csv_bytes = b"name,email\nJane Doe,jane@customer.example\n"

        response = await client.post(
            "/api/v1/imports/csv",
            data={"import_type": "customers"},
            files={"file": ("customers.csv", csv_bytes, "text/csv")},
            headers=_auth(token),
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "queued"
        assert body["filename"] == "customers.csv"
        assert len(dispatched) == 1
    finally:
        _clear_dispatcher_override()


async def test_upload_rejects_non_csv_file(client: AsyncClient):
    dispatched: list = []
    _override_dispatcher(dispatched)
    try:
        token = await _register(client)
        response = await client.post(
            "/api/v1/imports/csv",
            data={"import_type": "customers"},
            files={"file": ("customers.txt", b"name,email\n", "text/plain")},
            headers=_auth(token),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"
    finally:
        _clear_dispatcher_override()


async def test_member_cannot_upload_csv(client: AsyncClient, db_session):
    dispatched: list = []
    _override_dispatcher(dispatched)
    try:
        owner_token = await _register(client)
        me = await client.get("/api/v1/me", headers=_auth(owner_token))
        org_id = me.json()["organization_id"]

        user = User(
            email="member@acme.example",
            password_hash=hash_password("supersecret123"),
            full_name="Mel Member",
        )
        db_session.add(user)
        await db_session.flush()
        db_session.add(
            OrganizationMember(organization_id=org_id, user_id=user.id, role=Role.MEMBER)
        )
        await db_session.commit()

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "member@acme.example", "password": "supersecret123"},
        )
        member_token = login.json()["access_token"]

        response = await client.post(
            "/api/v1/imports/csv",
            data={"import_type": "customers"},
            files={"file": ("customers.csv", b"name,email\n", "text/csv")},
            headers=_auth(member_token),
        )
        assert response.status_code == 403
    finally:
        _clear_dispatcher_override()


async def test_get_import_job_tenant_isolation(client: AsyncClient):
    dispatched: list = []
    _override_dispatcher(dispatched)
    try:
        token_a = await _register(client, email="ownera@a.example", org="Org A")
        token_b = await _register(client, email="ownerb@b.example", org="Org B")

        create_response = await client.post(
            "/api/v1/imports/csv",
            data={"import_type": "customers"},
            files={"file": ("customers.csv", b"name,email\n", "text/csv")},
            headers=_auth(token_a),
        )
        job_id = create_response.json()["id"]

        response_b = await client.get(f"/api/v1/imports/{job_id}", headers=_auth(token_b))
        assert response_b.status_code == 404
    finally:
        _clear_dispatcher_override()
