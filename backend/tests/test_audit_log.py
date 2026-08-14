import json

from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.main import app
from app.modules.ai.dependencies import get_ai_service
from app.modules.ai.schemas import AIToolCall, AIToolResponse, AIUsageInfo
from app.modules.ai.service import AIService
from app.modules.audit.models import AuditLog
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


async def test_register_writes_audit_log_entry(client: AsyncClient, db_session):
    await _register(client)

    entries = (await db_session.execute(select(AuditLog))).scalars().all()
    actions = [e.action for e in entries]
    assert "auth.register" in actions


async def test_login_writes_audit_log_entry(client: AsyncClient, db_session):
    await _register(client)
    await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.example", "password": "supersecret123"},
    )

    entries = (await db_session.execute(select(AuditLog))).scalars().all()
    actions = [e.action for e in entries]
    assert actions.count("auth.login") == 1


async def test_customer_delete_writes_audit_log_entry(client: AsyncClient, db_session):
    token = await _register(client)
    create_response = await client.post(
        "/api/v1/customers",
        json={"name": "Temp Customer", "email": "temp@customer.example"},
        headers=_auth(token),
    )
    customer_id = create_response.json()["id"]

    await client.delete(f"/api/v1/customers/{customer_id}", headers=_auth(token))

    entries = (await db_session.execute(select(AuditLog))).scalars().all()
    delete_entries = [e for e in entries if e.action == "customer.deleted"]
    assert len(delete_entries) == 1
    assert str(delete_entries[0].entity_id) == customer_id


async def test_owner_can_list_audit_logs(client: AsyncClient):
    token = await _register(client)
    response = await client.get("/api/v1/audit-logs", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["items"][0]["action"]


async def test_member_cannot_list_audit_logs(client: AsyncClient, db_session):
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

    response = await client.get("/api/v1/audit-logs", headers=_auth(member_token))
    assert response.status_code == 403


async def test_audit_logs_scoped_to_organization(client: AsyncClient):
    token_a = await _register(client, email="ownera@a.example", org="Org A")
    token_b = await _register(client, email="ownerb@b.example", org="Org B")

    list_a = await client.get("/api/v1/audit-logs", headers=_auth(token_a))
    list_b = await client.get("/api/v1/audit-logs", headers=_auth(token_b))

    # Each org should only see its own register/login events, not the other's.
    assert list_a.json()["total"] == 1
    assert list_b.json()["total"] == 1


async def test_ai_create_task_writes_audit_log_with_metadata(client: AsyncClient, db_session):
    structured_answer = json.dumps(
        {"answer": "Done.", "insights": [], "recommendations": [], "suggested_tasks": []}
    )

    class ScriptedToolProvider:
        def __init__(self):
            self._calls = 0

        async def generate_with_tools(self, *, model, messages, tools, **kwargs):
            self._calls += 1
            if self._calls == 1:
                return AIToolResponse(
                    content=None,
                    tool_calls=[
                        AIToolCall(
                            id="call_1",
                            name="create_task",
                            arguments={"title": "Investigate Product A"},
                        )
                    ],
                    model="gpt-oss-120b",
                    provider="stub",
                    usage=AIUsageInfo(input_tokens=10, output_tokens=5, latency_ms=10),
                )
            return AIToolResponse(
                content=structured_answer,
                tool_calls=[],
                model="gpt-oss-120b",
                provider="stub",
                usage=AIUsageInfo(input_tokens=10, output_tokens=5, latency_ms=10),
            )

    app.dependency_overrides[get_ai_service] = lambda: AIService(ScriptedToolProvider())
    try:
        token = await _register(client)
        create_response = await client.post(
            "/api/v1/ai/conversations", json={}, headers=_auth(token)
        )
        conversation_id = create_response.json()["id"]

        response = await client.post(
            f"/api/v1/ai/conversations/{conversation_id}/messages",
            json={"content": "Create a task", "allow_ai_actions": True},
            headers=_auth(token),
        )
        assert response.status_code == 200

        entries = (await db_session.execute(select(AuditLog))).scalars().all()
        ai_entries = [e for e in entries if e.action == "ai.task_created"]
        assert len(ai_entries) == 1
        metadata = json.loads(ai_entries[0].event_metadata)
        assert metadata["title"] == "Investigate Product A"
    finally:
        app.dependency_overrides.pop(get_ai_service, None)
