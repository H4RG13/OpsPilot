"""seed demo data (Acme Commerce)

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-29

Dev/staging dummy data: one "Acme Commerce" organization with an OWNER,
ADMIN and MEMBER account, plus customers, products, ~90 days of orders and
a handful of tasks — enough for the dashboard/analytics views to have
something to show.

Every row uses a deterministic UUID, so downgrade() deletes exactly what
upgrade() inserted and leaves any other data alone. Full reset:

    docker compose exec backend alembic downgrade base
    docker compose exec backend alembic upgrade head

Skipped (no-op) when APP_ENV=production, and when the demo org or any of
its accounts already exist.
"""
import random
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.config import settings
from app.core.security import hash_password

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NAMESPACE = uuid.UUID("6f1c2a4e-3b7d-4c1a-9e8f-0a5b6c7d8e9f")


def _id(key: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, key)


ORG_ID = _id("org")
ORG_NAME = "Acme Commerce"
PASSWORD = "supersecret123"

# (key, email, full name, role)
USERS = [
    ("owner", "owner@acme-commerce.example", "Olivia Owner", "OWNER"),
    ("admin", "admin@acme-commerce.example", "Adam Admin", "ADMIN"),
    ("member", "member@acme-commerce.example", "Mia Member", "MEMBER"),
]

# (name, email, status)
CUSTOMERS = [
    ("Jane Doe", "jane.doe@customer.example", "ACTIVE"),
    ("John Smith", "john.smith@customer.example", "ACTIVE"),
    ("Maria Garcia", "maria.garcia@customer.example", "ACTIVE"),
    ("Wei Chen", "wei.chen@customer.example", "ACTIVE"),
    ("Aisha Khan", "aisha.khan@customer.example", "ACTIVE"),
    ("Liam O'Brien", "liam.obrien@customer.example", "AT_RISK"),
    ("Sofia Rossi", "sofia.rossi@customer.example", "AT_RISK"),
    ("Kenji Tanaka", "kenji.tanaka@customer.example", "ACTIVE"),
    ("Emma Wilson", "emma.wilson@customer.example", "INACTIVE"),
    ("Carlos Mendes", "carlos.mendes@customer.example", "ACTIVE"),
]

# (name, category, price, active)
PRODUCTS = [
    ("Wireless Mouse", "Electronics", "24.99", True),
    ("Mechanical Keyboard", "Electronics", "89.99", True),
    ("USB-C Hub", "Electronics", "39.99", True),
    ("27\" Monitor", "Electronics", "249.00", True),
    ("Standing Desk", "Furniture", "399.00", True),
    ("Ergonomic Chair", "Furniture", "289.00", True),
    ("Desk Lamp", "Furniture", "34.50", True),
    ("Notebook Pack", "Stationery", "12.00", True),
    ("Gel Pen Set", "Stationery", "8.75", True),
    ("Legacy Webcam", "Electronics", "19.99", False),
]

# (title, priority, status, due in N days or None, assignee key or None)
TASKS = [
    ("Follow up with at-risk customers", "HIGH", "OPEN", 2, "admin"),
    ("Restock Standing Desk inventory", "MEDIUM", "IN_PROGRESS", 5, "member"),
    ("Review Q3 sales report", "MEDIUM", "OPEN", 7, "owner"),
    ("Retire Legacy Webcam listing", "LOW", "DONE", None, "member"),
    ("Call Emma Wilson about reactivation", "HIGH", "OPEN", 1, "admin"),
    ("Update product categories", "LOW", "CANCELLED", None, None),
]

ORDER_COUNT = 60
ORDER_DAYS_BACK = 90


def _tables():
    uuid_col = postgresql.UUID(as_uuid=True)
    return {
        "organizations": sa.table(
            "organizations", sa.column("id", uuid_col), sa.column("name", sa.String)
        ),
        "users": sa.table(
            "users",
            sa.column("id", uuid_col),
            sa.column("email", sa.String),
            sa.column("password_hash", sa.String),
            sa.column("full_name", sa.String),
        ),
        "organization_members": sa.table(
            "organization_members",
            sa.column("organization_id", uuid_col),
            sa.column("user_id", uuid_col),
            sa.column("role", sa.String),
        ),
        "customers": sa.table(
            "customers",
            sa.column("id", uuid_col),
            sa.column("organization_id", uuid_col),
            sa.column("name", sa.String),
            sa.column("email", sa.String),
            sa.column("status", sa.String),
            sa.column("lifetime_value", sa.Numeric),
            sa.column("created_at", sa.DateTime(timezone=True)),
        ),
        "products": sa.table(
            "products",
            sa.column("id", uuid_col),
            sa.column("organization_id", uuid_col),
            sa.column("name", sa.String),
            sa.column("category", sa.String),
            sa.column("price", sa.Numeric),
            sa.column("active", sa.Boolean),
        ),
        "orders": sa.table(
            "orders",
            sa.column("id", uuid_col),
            sa.column("organization_id", uuid_col),
            sa.column("customer_id", uuid_col),
            sa.column("status", sa.String),
            sa.column("total_amount", sa.Numeric),
            sa.column("ordered_at", sa.DateTime(timezone=True)),
        ),
        "order_items": sa.table(
            "order_items",
            sa.column("id", uuid_col),
            sa.column("order_id", uuid_col),
            sa.column("product_id", uuid_col),
            sa.column("quantity", sa.Integer),
            sa.column("unit_price", sa.Numeric),
            sa.column("subtotal", sa.Numeric),
        ),
        "tasks": sa.table(
            "tasks",
            sa.column("id", uuid_col),
            sa.column("organization_id", uuid_col),
            sa.column("created_by", uuid_col),
            sa.column("assigned_to", uuid_col),
            sa.column("title", sa.String),
            sa.column("priority", sa.String),
            sa.column("status", sa.String),
            sa.column("due_date", sa.Date),
        ),
    }


def _already_seeded(conn) -> bool:
    org_exists = conn.execute(
        sa.text("SELECT 1 FROM organizations WHERE id = :id"), {"id": ORG_ID}
    ).first()
    user_exists = conn.execute(
        sa.text("SELECT 1 FROM users WHERE email IN :emails").bindparams(
            sa.bindparam("emails", expanding=True)
        ),
        {"emails": [email for _, email, _, _ in USERS]},
    ).first()
    return bool(org_exists or user_exists)


def upgrade() -> None:
    if settings.is_production:
        print("0009: APP_ENV=production — skipping demo seed data.")
        return
    conn = op.get_bind()
    if _already_seeded(conn):
        print("0009: demo org/accounts already exist — skipping demo seed data.")
        return

    t = _tables()
    now = datetime.now(UTC)
    today = now.date()
    rng = random.Random(42)  # fixed seed → same dataset every run

    op.bulk_insert(t["organizations"], [{"id": ORG_ID, "name": ORG_NAME}])

    password_hash = hash_password(PASSWORD)
    op.bulk_insert(
        t["users"],
        [
            {"id": _id(f"user:{key}"), "email": email, "password_hash": password_hash,
             "full_name": name}
            for key, email, name, _ in USERS
        ],
    )
    op.bulk_insert(
        t["organization_members"],
        [
            {"organization_id": ORG_ID, "user_id": _id(f"user:{key}"), "role": role}
            for key, _, _, role in USERS
        ],
    )

    op.bulk_insert(
        t["products"],
        [
            {"id": _id(f"product:{i}"), "organization_id": ORG_ID, "name": name,
             "category": category, "price": Decimal(price), "active": active}
            for i, (name, category, price, active) in enumerate(PRODUCTS)
        ],
    )

    # Orders: random customer, 1–3 distinct active products each, spread over
    # the last ORDER_DAYS_BACK days. Recent ones are more likely to be pending.
    active_products = [
        (_id(f"product:{i}"), Decimal(price))
        for i, (_, _, price, active) in enumerate(PRODUCTS)
        if active
    ]
    lifetime_value = {i: Decimal("0") for i in range(len(CUSTOMERS))}
    orders, items = [], []
    for n in range(ORDER_COUNT):
        customer_idx = rng.randrange(len(CUSTOMERS))
        days_ago = rng.randrange(ORDER_DAYS_BACK)
        ordered_at = now - timedelta(days=days_ago, hours=rng.randrange(24))
        roll = rng.random()
        if days_ago < 7 and roll < 0.6:
            status = "PENDING"
        elif roll < 0.1:
            status = "CANCELLED"
        else:
            status = "COMPLETED"

        order_id = _id(f"order:{n}")
        total = Decimal("0")
        for m, (product_id, price) in enumerate(rng.sample(active_products, rng.randint(1, 3))):
            quantity = rng.randint(1, 4)
            subtotal = price * quantity
            total += subtotal
            items.append({"id": _id(f"order:{n}:item:{m}"), "order_id": order_id,
                          "product_id": product_id, "quantity": quantity,
                          "unit_price": price, "subtotal": subtotal})
        orders.append({"id": order_id, "organization_id": ORG_ID,
                       "customer_id": _id(f"customer:{customer_idx}"), "status": status,
                       "total_amount": total, "ordered_at": ordered_at})
        if status == "COMPLETED":
            lifetime_value[customer_idx] += total

    op.bulk_insert(
        t["customers"],
        [
            {"id": _id(f"customer:{i}"), "organization_id": ORG_ID, "name": name,
             "email": email, "status": status, "lifetime_value": lifetime_value[i],
             "created_at": now - timedelta(days=ORDER_DAYS_BACK + 30 - i)}
            for i, (name, email, status) in enumerate(CUSTOMERS)
        ],
    )
    op.bulk_insert(t["orders"], orders)
    op.bulk_insert(t["order_items"], items)

    op.bulk_insert(
        t["tasks"],
        [
            {"id": _id(f"task:{i}"), "organization_id": ORG_ID,
             "created_by": _id("user:owner"),
             "assigned_to": _id(f"user:{assignee}") if assignee else None,
             "title": title, "priority": priority, "status": status,
             "due_date": today + timedelta(days=due) if due is not None else None}
            for i, (title, priority, status, due, assignee) in enumerate(TASKS)
        ],
    )


def downgrade() -> None:
    conn = op.get_bind()
    # Orders RESTRICT-reference customers/products, so they go first (items
    # cascade). Deleting the org then cascades members, customers, products,
    # tasks and anything else created under it (AI usage, reports, etc.).
    conn.execute(sa.text("DELETE FROM orders WHERE organization_id = :id"), {"id": ORG_ID})
    conn.execute(sa.text("DELETE FROM organizations WHERE id = :id"), {"id": ORG_ID})
    conn.execute(
        sa.text("DELETE FROM users WHERE id IN :ids").bindparams(
            sa.bindparam("ids", expanding=True)
        ),
        {"ids": [_id(f"user:{key}") for key, _, _, _ in USERS]},
    )
