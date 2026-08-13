import uuid

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


async def _create_customer(client: AsyncClient, token: str) -> str:
    response = await client.post(
        "/api/v1/customers",
        json={"name": "Jane Doe", "email": "jane@customer.example"},
        headers=_auth(token),
    )
    return response.json()["id"]


async def _create_product(client: AsyncClient, token: str, price: str = "10.00") -> str:
    response = await client.post(
        "/api/v1/products",
        json={"name": "Widget", "category": "Hardware", "price": price},
        headers=_auth(token),
    )
    return response.json()["id"]


async def test_create_order_computes_totals_from_products(client: AsyncClient):
    token = await _register(client)
    customer_id = await _create_customer(client, token)
    product_id = await _create_product(client, token, price="10.00")

    response = await client.post(
        "/api/v1/orders",
        json={"customer_id": customer_id, "items": [{"product_id": product_id, "quantity": 3}]},
        headers=_auth(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["total_amount"] == "30.00"
    assert body["items"][0]["unit_price"] == "10.00"
    assert body["items"][0]["subtotal"] == "30.00"


async def test_create_order_rejects_unknown_customer(client: AsyncClient):
    token = await _register(client)
    product_id = await _create_product(client, token)

    response = await client.post(
        "/api/v1/orders",
        json={
            "customer_id": str(uuid.uuid4()),
            "items": [{"product_id": product_id, "quantity": 1}],
        },
        headers=_auth(token),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CUSTOMER_NOT_FOUND"


async def test_create_order_rejects_unknown_product(client: AsyncClient):
    token = await _register(client)
    customer_id = await _create_customer(client, token)

    response = await client.post(
        "/api/v1/orders",
        json={
            "customer_id": customer_id,
            "items": [{"product_id": str(uuid.uuid4()), "quantity": 1}],
        },
        headers=_auth(token),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


async def test_update_order_status(client: AsyncClient):
    token = await _register(client)
    customer_id = await _create_customer(client, token)
    product_id = await _create_product(client, token)

    create_response = await client.post(
        "/api/v1/orders",
        json={"customer_id": customer_id, "items": [{"product_id": product_id, "quantity": 1}]},
        headers=_auth(token),
    )
    order_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/orders/{order_id}", json={"status": "completed"}, headers=_auth(token)
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "completed"


async def test_member_cannot_create_order(client: AsyncClient, db_session):
    owner_token = await _register(client)
    me_response = await client.get("/api/v1/me", headers=_auth(owner_token))
    org_id = me_response.json()["organization_id"]

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

    customer_id = await _create_customer(client, owner_token)
    product_id = await _create_product(client, owner_token)

    response = await client.post(
        "/api/v1/orders",
        json={"customer_id": customer_id, "items": [{"product_id": product_id, "quantity": 1}]},
        headers=_auth(member_token),
    )
    assert response.status_code == 403


async def test_order_tenant_isolation(client: AsyncClient):
    token_a = await _register(client, email="ownera@a.example", org="Org A")
    token_b = await _register(client, email="ownerb@b.example", org="Org B")

    customer_id = await _create_customer(client, token_a)
    product_id = await _create_product(client, token_a)

    create_response = await client.post(
        "/api/v1/orders",
        json={"customer_id": customer_id, "items": [{"product_id": product_id, "quantity": 1}]},
        headers=_auth(token_a),
    )
    order_id = create_response.json()["id"]

    cross_tenant_response = await client.get(f"/api/v1/orders/{order_id}", headers=_auth(token_b))
    assert cross_tenant_response.status_code == 404
