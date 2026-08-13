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
    body = response.json()
    return body["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _add_member(client: AsyncClient, db_session, organization_id, email: str) -> str:
    user = User(
        email=email, password_hash=hash_password("supersecret123"), full_name="Mel Member"
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        OrganizationMember(organization_id=organization_id, user_id=user.id, role=Role.MEMBER)
    )
    await db_session.commit()

    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret123"}
    )
    return login.json()["access_token"]


async def _get_org_id(client: AsyncClient, token: str) -> str:
    response = await client.get("/api/v1/me", headers=_auth(token))
    return response.json()["organization_id"]


async def test_owner_can_create_and_read_customer(client: AsyncClient):
    token = await _register(client)
    response = await client.post(
        "/api/v1/customers",
        json={"name": "Jane Doe", "email": "jane@customer.example"},
        headers=_auth(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Jane Doe"
    assert body["status"] == "active"
    assert body["lifetime_value"] == "0.00" or body["lifetime_value"] == "0"

    get_response = await client.get(f"/api/v1/customers/{body['id']}", headers=_auth(token))
    assert get_response.status_code == 200


async def test_member_can_read_but_not_write_customer(client: AsyncClient, db_session):
    owner_token = await _register(client)
    org_id = await _get_org_id(client, owner_token)
    member_token = await _add_member(client, db_session, org_id, "member@acme.example")

    list_response = await client.get("/api/v1/customers", headers=_auth(member_token))
    assert list_response.status_code == 200

    create_response = await client.post(
        "/api/v1/customers",
        json={"name": "Blocked", "email": "blocked@customer.example"},
        headers=_auth(member_token),
    )
    assert create_response.status_code == 403
    assert create_response.json()["error"]["code"] == "INSUFFICIENT_ROLE"


async def test_customer_search_and_status_filter(client: AsyncClient):
    token = await _register(client)
    await client.post(
        "/api/v1/customers",
        json={"name": "Alice Alpha", "email": "alice@customer.example", "status": "active"},
        headers=_auth(token),
    )
    await client.post(
        "/api/v1/customers",
        json={"name": "Bob Beta", "email": "bob@customer.example", "status": "at_risk"},
        headers=_auth(token),
    )

    search_response = await client.get(
        "/api/v1/customers", params={"search": "Alpha"}, headers=_auth(token)
    )
    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["total"] == 1
    assert search_body["items"][0]["name"] == "Alice Alpha"

    status_response = await client.get(
        "/api/v1/customers", params={"status": "at_risk"}, headers=_auth(token)
    )
    status_body = status_response.json()
    assert status_body["total"] == 1
    assert status_body["items"][0]["name"] == "Bob Beta"


async def test_customer_update_and_delete(client: AsyncClient):
    token = await _register(client)
    create_response = await client.post(
        "/api/v1/customers",
        json={"name": "Temp Customer", "email": "temp@customer.example"},
        headers=_auth(token),
    )
    customer_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"status": "inactive"},
        headers=_auth(token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "inactive"

    delete_response = await client.delete(
        f"/api/v1/customers/{customer_id}", headers=_auth(token)
    )
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/customers/{customer_id}", headers=_auth(token))
    assert get_response.status_code == 404
    assert get_response.json()["error"]["code"] == "CUSTOMER_NOT_FOUND"


async def test_customer_tenant_isolation(client: AsyncClient):
    token_a = await _register(client, email="ownera@a.example", org="Org A")
    token_b = await _register(client, email="ownerb@b.example", org="Org B")

    create_response = await client.post(
        "/api/v1/customers",
        json={"name": "Org A Customer", "email": "a@customer.example"},
        headers=_auth(token_a),
    )
    customer_id = create_response.json()["id"]

    cross_tenant_response = await client.get(
        f"/api/v1/customers/{customer_id}", headers=_auth(token_b)
    )
    assert cross_tenant_response.status_code == 404
