import uuid
from decimal import Decimal

from httpx import AsyncClient

from app.core.security import hash_password
from app.modules.ai.models import AIUsage
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


async def test_owner_can_list_usage(client: AsyncClient, db_session):
    token = await _register(client)
    me = await client.get("/api/v1/me", headers=_auth(token))
    org_id = me.json()["organization_id"]

    db_session.add(
        AIUsage(
            id=uuid.uuid4(),
            organization_id=uuid.UUID(org_id),
            user_id=None,
            provider="groq",
            model="gpt-oss-20b",
            task_type="summary",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
            estimated_cost=Decimal("0.001"),
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/ai/usage", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["model"] == "gpt-oss-20b"


async def test_member_cannot_list_usage(client: AsyncClient, db_session):
    token = await _register(client)
    me = await client.get("/api/v1/me", headers=_auth(token))
    org_id = me.json()["organization_id"]

    user = User(
        email="member@acme.example",
        password_hash=hash_password("supersecret123"),
        full_name="Mel Member",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        OrganizationMember(organization_id=uuid.UUID(org_id), user_id=user.id, role=Role.MEMBER)
    )
    await db_session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@acme.example", "password": "supersecret123"},
    )
    member_token = login.json()["access_token"]

    response = await client.get("/api/v1/ai/usage", headers=_auth(member_token))
    assert response.status_code == 403


async def test_usage_scoped_to_organization(client: AsyncClient, db_session):
    token_a = await _register(client, email="ownera@a.example", org="Org A")
    me_a = await client.get("/api/v1/me", headers=_auth(token_a))
    org_a_id = me_a.json()["organization_id"]

    token_b = await _register(client, email="ownerb@b.example", org="Org B")

    db_session.add(
        AIUsage(
            id=uuid.uuid4(),
            organization_id=uuid.UUID(org_a_id),
            user_id=None,
            provider="groq",
            model="gpt-oss-20b",
            task_type="summary",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
            estimated_cost=Decimal("0.001"),
        )
    )
    await db_session.commit()

    response_b = await client.get("/api/v1/ai/usage", headers=_auth(token_b))
    assert response_b.status_code == 200
    assert response_b.json()["total"] == 0
