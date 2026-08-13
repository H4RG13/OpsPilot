from httpx import AsyncClient


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


async def test_create_and_get_product(client: AsyncClient):
    token = await _register(client)
    response = await client.post(
        "/api/v1/products",
        json={"name": "Widget", "category": "Hardware", "price": "19.99"},
        headers=_auth(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Widget"
    assert body["active"] is True

    get_response = await client.get(f"/api/v1/products/{body['id']}", headers=_auth(token))
    assert get_response.status_code == 200


async def test_product_category_and_active_filters(client: AsyncClient):
    token = await _register(client)
    await client.post(
        "/api/v1/products",
        json={"name": "Widget", "category": "Hardware", "price": "10.00"},
        headers=_auth(token),
    )
    await client.post(
        "/api/v1/products",
        json={"name": "Gadget", "category": "Electronics", "price": "20.00", "active": False},
        headers=_auth(token),
    )

    category_response = await client.get(
        "/api/v1/products", params={"category": "Hardware"}, headers=_auth(token)
    )
    assert category_response.json()["total"] == 1

    active_response = await client.get(
        "/api/v1/products", params={"active": False}, headers=_auth(token)
    )
    assert active_response.json()["total"] == 1
    assert active_response.json()["items"][0]["name"] == "Gadget"


async def test_product_price_must_be_positive(client: AsyncClient):
    token = await _register(client)
    response = await client.post(
        "/api/v1/products",
        json={"name": "Freebie", "category": "Misc", "price": "0"},
        headers=_auth(token),
    )
    assert response.status_code == 422


async def test_product_tenant_isolation(client: AsyncClient):
    token_a = await _register(client, email="ownera@a.example", org="Org A")
    token_b = await _register(client, email="ownerb@b.example", org="Org B")

    create_response = await client.post(
        "/api/v1/products",
        json={"name": "Org A Product", "category": "Misc", "price": "5.00"},
        headers=_auth(token_a),
    )
    product_id = create_response.json()["id"]

    cross_tenant_response = await client.get(
        f"/api/v1/products/{product_id}", headers=_auth(token_b)
    )
    assert cross_tenant_response.status_code == 404
