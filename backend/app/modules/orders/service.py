from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.customers.models import Customer
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.orders.schemas import OrderCreate
from app.modules.products.models import Product
from app.shared.exceptions import NotFoundError
from app.shared.pagination import Page, PageParams


async def create_order(db: AsyncSession, organization_id: uuid.UUID, data: OrderCreate) -> Order:
    customer_stmt = select(Customer).where(
        Customer.id == data.customer_id, Customer.organization_id == organization_id
    )
    customer = (await db.execute(customer_stmt)).scalar_one_or_none()
    if customer is None:
        raise NotFoundError("Customer was not found.", code="CUSTOMER_NOT_FOUND")

    product_ids = [item.product_id for item in data.items]
    products_stmt = select(Product).where(
        Product.id.in_(product_ids), Product.organization_id == organization_id
    )
    products_by_id = {p.id: p for p in (await db.execute(products_stmt)).scalars().all()}

    missing = set(product_ids) - set(products_by_id)
    if missing:
        raise NotFoundError(
            f"Unknown product id(s): {', '.join(str(pid) for pid in missing)}",
            code="PRODUCT_NOT_FOUND",
        )

    order_items = []
    total_amount = Decimal("0")
    for item in data.items:
        product = products_by_id[item.product_id]
        subtotal = product.price * item.quantity
        total_amount += subtotal
        order_items.append(
            OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.price,
                subtotal=subtotal,
            )
        )

    order = Order(
        organization_id=organization_id,
        customer_id=data.customer_id,
        status=OrderStatus.PENDING,
        total_amount=total_amount,
        items=order_items,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order, attribute_names=["items"])
    return order


async def get_order(db: AsyncSession, organization_id: uuid.UUID, order_id: uuid.UUID) -> Order:
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.organization_id == organization_id)
    )
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise NotFoundError("Order was not found.", code="ORDER_NOT_FOUND")
    return order


async def list_orders(
    db: AsyncSession,
    organization_id: uuid.UUID,
    params: PageParams,
    status: OrderStatus | None = None,
) -> Page[Order]:
    conditions = [Order.organization_id == organization_id]
    if status is not None:
        conditions.append(Order.status == status)

    count_stmt = select(func.count()).select_from(Order).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    list_stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(*conditions)
        .order_by(Order.ordered_at.desc())
        .offset(params.offset)
        .limit(params.page_size)
    )
    items = list((await db.execute(list_stmt)).scalars().all())

    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


async def update_order_status(
    db: AsyncSession, organization_id: uuid.UUID, order_id: uuid.UUID, status: OrderStatus
) -> Order:
    order = await get_order(db, organization_id, order_id)
    order.status = status
    await db.commit()
    await db.refresh(order, attribute_names=["items"])
    return order
