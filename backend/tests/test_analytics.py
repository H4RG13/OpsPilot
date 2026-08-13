import uuid
from datetime import UTC, date, datetime, timedelta

from httpx import AsyncClient

from app.modules.orders.models import Order, OrderItem, OrderStatus


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


async def _create_customer(
    client: AsyncClient, token: str, email: str = "jane@customer.example"
) -> str:
    response = await client.post(
        "/api/v1/customers",
        json={"name": "Jane Doe", "email": email},
        headers=_auth(token),
    )
    return response.json()["id"]


async def _create_product(client: AsyncClient, token: str, name: str, price: str) -> str:
    response = await client.post(
        "/api/v1/products",
        json={"name": name, "category": "General", "price": price},
        headers=_auth(token),
    )
    return response.json()["id"]


async def _insert_order(
    db_session,
    organization_id: str,
    customer_id: str,
    product_id: str,
    *,
    quantity: int,
    unit_price: str,
    status: OrderStatus,
    ordered_at: datetime,
) -> None:
    subtotal = int(quantity) * float(unit_price)
    order = Order(
        id=uuid.uuid4(),
        organization_id=uuid.UUID(organization_id),
        customer_id=uuid.UUID(customer_id),
        status=status,
        total_amount=subtotal,
        ordered_at=ordered_at,
    )
    db_session.add(order)
    await db_session.flush()
    db_session.add(
        OrderItem(
            id=uuid.uuid4(),
            order_id=order.id,
            product_id=uuid.UUID(product_id),
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal,
        )
    )
    await db_session.commit()


async def _setup_seeded_org(client: AsyncClient, db_session):
    token = await _register(client)
    me = await client.get("/api/v1/me", headers=_auth(token))
    org_id = me.json()["organization_id"]

    customer_id = await _create_customer(client, token)
    product_a = await _create_product(client, token, "Widget", "10.00")
    product_b = await _create_product(client, token, "Gadget", "20.00")

    now = datetime.now(UTC).replace(tzinfo=None)
    await _insert_order(
        db_session, org_id, customer_id, product_a,
        quantity=2, unit_price="10.00", status=OrderStatus.COMPLETED,
        ordered_at=now - timedelta(days=2),
    )
    await _insert_order(
        db_session, org_id, customer_id, product_b,
        quantity=1, unit_price="20.00", status=OrderStatus.PENDING,
        ordered_at=now - timedelta(days=1),
    )
    await _insert_order(
        db_session, org_id, customer_id, product_a,
        quantity=5, unit_price="10.00", status=OrderStatus.CANCELLED,
        ordered_at=now - timedelta(days=1),
    )

    return token, org_id, customer_id, product_a, product_b


async def test_overview_excludes_cancelled_orders(client: AsyncClient, db_session):
    token, *_ = await _setup_seeded_org(client, db_session)

    response = await client.get(
        "/api/v1/analytics/overview",
        params={
            "start_date": (date.today() - timedelta(days=7)).isoformat(),
            "end_date": date.today().isoformat(),
        },
        headers=_auth(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["revenue"] == "40.00"
    assert body["order_count"] == 2
    assert body["average_order_value"] == "20.00"
    assert body["total_customers"] == 1
    assert body["active_customers"] == 1


async def test_revenue_trend_buckets_by_day(client: AsyncClient, db_session):
    token, *_ = await _setup_seeded_org(client, db_session)

    response = await client.get(
        "/api/v1/analytics/revenue",
        params={
            "start_date": (date.today() - timedelta(days=7)).isoformat(),
            "end_date": date.today().isoformat(),
            "granularity": "day",
        },
        headers=_auth(token),
    )
    assert response.status_code == 200
    points = response.json()["points"]
    assert len(points) == 2
    revenues = sorted(float(p["revenue"]) for p in points)
    assert revenues == [20.0, 20.0]


async def test_product_performance_ranks_by_revenue(client: AsyncClient, db_session):
    token, *_ = await _setup_seeded_org(client, db_session)

    response = await client.get(
        "/api/v1/analytics/products",
        params={
            "start_date": (date.today() - timedelta(days=7)).isoformat(),
            "end_date": date.today().isoformat(),
        },
        headers=_auth(token),
    )
    assert response.status_code == 200
    products = response.json()["products"]
    assert len(products) == 2
    assert products[0]["name"] == "Gadget"
    assert products[0]["revenue"] == "20.00"
    assert products[1]["name"] == "Widget"
    assert products[1]["revenue"] == "20.00"
    assert products[1]["quantity_sold"] == 2


async def test_customer_metrics(client: AsyncClient, db_session):
    token, *_ = await _setup_seeded_org(client, db_session)

    response = await client.get(
        "/api/v1/analytics/customers",
        params={
            "start_date": (date.today() - timedelta(days=7)).isoformat(),
            "end_date": date.today().isoformat(),
        },
        headers=_auth(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_customers"] == 1
    assert body["new_customers"] == 1
    assert body["active_customers"] == 1
    assert body["at_risk_customers"] == 0


async def test_analytics_rejects_invalid_date_range(client: AsyncClient):
    token = await _register(client)
    response = await client.get(
        "/api/v1/analytics/overview",
        params={"start_date": "2026-01-10", "end_date": "2026-01-01"},
        headers=_auth(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DATE_RANGE"


async def test_analytics_defaults_to_last_30_days(client: AsyncClient):
    token = await _register(client)
    response = await client.get("/api/v1/analytics/overview", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body["start_date"] and body["end_date"]


async def test_analytics_tenant_isolation(client: AsyncClient, db_session):
    token_a, org_a, *_ = await _setup_seeded_org(client, db_session)
    token_b = await _register(client, email="ownerb@b.example", org="Org B")

    response_b = await client.get(
        "/api/v1/analytics/overview",
        params={
            "start_date": (date.today() - timedelta(days=7)).isoformat(),
            "end_date": date.today().isoformat(),
        },
        headers=_auth(token_b),
    )
    assert response_b.status_code == 200
    assert response_b.json()["revenue"] == "0.00"
