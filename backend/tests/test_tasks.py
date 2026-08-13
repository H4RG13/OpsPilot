from httpx import AsyncClient

from app.core.security import hash_password
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


async def test_owner_can_create_and_read_task(client: AsyncClient):
    token = await _register(client)
    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Investigate Product A", "priority": "high"},
        headers=_auth(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Investigate Product A"
    assert body["status"] == "open"

    get_response = await client.get(f"/api/v1/tasks/{body['id']}", headers=_auth(token))
    assert get_response.status_code == 200


async def test_member_can_read_but_not_write_task(client: AsyncClient, db_session):
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

    list_response = await client.get("/api/v1/tasks", headers=_auth(member_token))
    assert list_response.status_code == 200

    create_response = await client.post(
        "/api/v1/tasks", json={"title": "Blocked"}, headers=_auth(member_token)
    )
    assert create_response.status_code == 403


async def test_task_status_and_priority_filters(client: AsyncClient):
    token = await _register(client)
    await client.post(
        "/api/v1/tasks", json={"title": "High priority", "priority": "high"}, headers=_auth(token)
    )
    low = await client.post(
        "/api/v1/tasks", json={"title": "Low priority", "priority": "low"}, headers=_auth(token)
    )
    await client.patch(
        f"/api/v1/tasks/{low.json()['id']}", json={"status": "done"}, headers=_auth(token)
    )

    priority_response = await client.get(
        "/api/v1/tasks", params={"priority": "high"}, headers=_auth(token)
    )
    assert priority_response.json()["total"] == 1

    status_response = await client.get(
        "/api/v1/tasks", params={"status": "done"}, headers=_auth(token)
    )
    assert status_response.json()["total"] == 1
    assert status_response.json()["items"][0]["title"] == "Low priority"


async def test_task_update(client: AsyncClient):
    token = await _register(client)
    create_response = await client.post(
        "/api/v1/tasks", json={"title": "Temp task"}, headers=_auth(token)
    )
    task_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/tasks/{task_id}", json={"status": "in_progress"}, headers=_auth(token)
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_progress"


async def test_task_tenant_isolation(client: AsyncClient):
    token_a = await _register(client, email="ownera@a.example", org="Org A")
    token_b = await _register(client, email="ownerb@b.example", org="Org B")

    create_response = await client.post(
        "/api/v1/tasks", json={"title": "Org A task"}, headers=_auth(token_a)
    )
    task_id = create_response.json()["id"]

    cross_tenant_response = await client.get(f"/api/v1/tasks/{task_id}", headers=_auth(token_b))
    assert cross_tenant_response.status_code == 404
