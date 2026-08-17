"""Idempotent dev-environment seed data: a demo org with an OWNER and an
ADMIN account, plus a small set of sample customers/products/orders/tasks.

Run inside the backend container (it needs the app's DATABASE_URL):

    docker compose exec backend python -m scripts.seed

Safe to re-run — every insert is guarded by a lookup, so running this
against a database that already has the demo org just leaves it as-is
and reports the existing accounts instead of duplicating anything.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.modules.customers.models import Customer, CustomerStatus
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.products.models import Product
from app.modules.tasks.models import Task, TaskPriority
from app.modules.users.models import User
from app.shared.permissions import Role

ORG_NAME = "Acme Demo"
OWNER_EMAIL = "demo@acme.example"
OWNER_PASSWORD = "supersecret123"
OWNER_NAME = "Demo User"
ADMIN_EMAIL = "admin@acme.example"
ADMIN_PASSWORD = "supersecret123"
ADMIN_NAME = "Admin User"


async def _get_or_create_user(
    db, *, email: str, password: str, full_name: str
) -> tuple[User, bool]:
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        return existing, False
    user = User(email=email, password_hash=hash_password(password), full_name=full_name)
    db.add(user)
    await db.flush()
    return user, True


async def _ensure_membership(db, *, organization_id, user_id, role: Role) -> None:
    existing = (
        await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return
    db.add(OrganizationMember(organization_id=organization_id, user_id=user_id, role=role))


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        organization = (
            await db.execute(select(Organization).where(Organization.name == ORG_NAME))
        ).scalar_one_or_none()
        if organization is None:
            organization = Organization(name=ORG_NAME)
            db.add(organization)
            await db.flush()
            print(f"Created organization '{ORG_NAME}'")
        else:
            print(f"Organization '{ORG_NAME}' already exists")

        owner, owner_created = await _get_or_create_user(
            db, email=OWNER_EMAIL, password=OWNER_PASSWORD, full_name=OWNER_NAME
        )
        await _ensure_membership(
            db, organization_id=organization.id, user_id=owner.id, role=Role.OWNER
        )
        print(f"{'Created' if owner_created else 'Found'} OWNER account: {OWNER_EMAIL}")

        admin, admin_created = await _get_or_create_user(
            db, email=ADMIN_EMAIL, password=ADMIN_PASSWORD, full_name=ADMIN_NAME
        )
        await _ensure_membership(
            db, organization_id=organization.id, user_id=admin.id, role=Role.ADMIN
        )
        print(f"{'Created' if admin_created else 'Found'} ADMIN account: {ADMIN_EMAIL}")

        await db.commit()

        has_customers = (
            await db.execute(select(Customer).where(Customer.organization_id == organization.id))
        ).first()
        if has_customers:
            print("Sample business data already present — skipping.")
        else:
            customer = Customer(
                organization_id=organization.id,
                name="Jane Doe",
                email="jane@customer.example",
                status=CustomerStatus.ACTIVE,
                lifetime_value=Decimal("0"),
            )
            widget = Product(
                organization_id=organization.id,
                name="Widget",
                category="Hardware",
                price=Decimal("19.99"),
            )
            gadget = Product(
                organization_id=organization.id,
                name="Gadget",
                category="Electronics",
                price=Decimal("49.99"),
            )
            db.add_all([customer, widget, gadget])
            await db.flush()

            order1 = Order(
                organization_id=organization.id, customer_id=customer.id, status=OrderStatus.PENDING
            )
            order2 = Order(
                organization_id=organization.id, customer_id=customer.id, status=OrderStatus.PENDING
            )
            db.add_all([order1, order2])
            await db.flush()

            order1_items = [
                OrderItem(
                    order_id=order1.id, product_id=widget.id, quantity=3,
                    unit_price=widget.price, subtotal=widget.price * 3,
                ),
                OrderItem(
                    order_id=order1.id, product_id=gadget.id, quantity=1,
                    unit_price=gadget.price, subtotal=gadget.price,
                ),
            ]
            order2_items = [
                OrderItem(
                    order_id=order2.id, product_id=gadget.id, quantity=2,
                    unit_price=gadget.price, subtotal=gadget.price * 2,
                ),
            ]
            db.add_all(order1_items + order2_items)
            order1.total_amount = sum((item.subtotal for item in order1_items), Decimal("0"))
            order2.total_amount = sum((item.subtotal for item in order2_items), Decimal("0"))

            db.add(
                Task(
                    organization_id=organization.id,
                    created_by=owner.id,
                    title="Follow up with Jane Doe",
                    priority=TaskPriority.HIGH,
                )
            )

            await db.commit()
            print("Seeded sample customer, products, orders, and a task.")

    await engine.dispose()

    print()
    print("Login credentials:")
    print(f"  Owner: {OWNER_EMAIL} / {OWNER_PASSWORD}")
    print(f"  Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
