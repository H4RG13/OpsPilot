from httpx import AsyncClient


async def _register(
    client: AsyncClient, email: str = "owner@acme.example", org: str = "Acme Commerce"
):
    return await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret123",
            "full_name": "Ada Owner",
            "organization_name": org,
        },
    )


async def test_register_creates_org_and_returns_tokens(client: AsyncClient):
    response = await _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_register_duplicate_email_conflicts(client: AsyncClient):
    await _register(client)
    response = await _register(client)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_login_with_valid_credentials(client: AsyncClient):
    await _register(client)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "owner@acme.example", "password": "supersecret123"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_login_with_invalid_password(client: AsyncClient):
    await _register(client)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "owner@acme.example", "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_with_unknown_email_returns_same_error_as_wrong_password(client: AsyncClient):
    # Same code/message as a wrong password for a real account — an unknown
    # email must not be distinguishable via the error response (no user
    # enumeration), and authenticate() still runs a dummy bcrypt comparison
    # so the two cases don't differ in timing either.
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@acme.example", "password": "whatever123"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_me_requires_authentication(client: AsyncClient):
    response = await client.get("/api/v1/me")
    assert response.status_code == 401


async def test_me_returns_user_and_org_context(client: AsyncClient):
    register_response = await _register(client)
    access_token = register_response.json()["access_token"]

    response = await client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "owner@acme.example"
    assert body["role"] == "owner"
    assert body["organization_id"]


async def test_organizations_current_scoped_to_caller(client: AsyncClient):
    register_response = await _register(client, email="a@acme.example", org="Acme Commerce")
    access_token = register_response.json()["access_token"]

    response = await client.get(
        "/api/v1/organizations/current", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Acme Commerce"


async def test_refresh_rotates_and_invalidates_old_token(client: AsyncClient):
    register_response = await _register(client)
    old_refresh_token = register_response.json()["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
    )
    assert refresh_response.status_code == 200
    new_refresh_token = refresh_response.json()["refresh_token"]
    assert new_refresh_token != old_refresh_token

    reuse_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
    )
    assert reuse_response.status_code == 401
    assert reuse_response.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"


async def test_logout_revokes_refresh_token(client: AsyncClient):
    register_response = await _register(client)
    refresh_token = register_response.json()["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_response.status_code == 204

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401


async def test_tenant_isolation_second_org_is_independent(client: AsyncClient):
    first = await _register(client, email="owner1@a.example", org="Org A")
    second = await _register(client, email="owner2@b.example", org="Org B")

    token_a = first.json()["access_token"]
    token_b = second.json()["access_token"]

    org_a = await client.get(
        "/api/v1/organizations/current", headers={"Authorization": f"Bearer {token_a}"}
    )
    org_b = await client.get(
        "/api/v1/organizations/current", headers={"Authorization": f"Bearer {token_b}"}
    )

    assert org_a.json()["name"] == "Org A"
    assert org_b.json()["name"] == "Org B"
    assert org_a.json()["id"] != org_b.json()["id"]
