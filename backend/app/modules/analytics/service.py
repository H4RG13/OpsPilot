import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customers.models import Customer, CustomerStatus
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.products.models import Product

# Orders still "booked" (not cancelled) count toward revenue/order metrics.
REVENUE_STATUSES = (OrderStatus.PENDING, OrderStatus.COMPLETED)


def _date_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(start_date, time.min)
    end_dt_exclusive = datetime.combine(end_date + timedelta(days=1), time.min)
    return start_dt, end_dt_exclusive


async def get_revenue_summary(
    db: AsyncSession, organization_id: uuid.UUID, start_date: date, end_date: date
) -> dict:
    start_dt, end_dt = _date_bounds(start_date, end_date)
    stmt = select(
        func.coalesce(func.sum(Order.total_amount), 0),
        func.count(Order.id),
    ).where(
        Order.organization_id == organization_id,
        Order.status.in_(REVENUE_STATUSES),
        Order.ordered_at >= start_dt,
        Order.ordered_at < end_dt,
    )
    revenue, order_count = (await db.execute(stmt)).one()
    revenue = Decimal(str(revenue))
    average_order_value = (revenue / order_count) if order_count else Decimal("0")
    return {
        "revenue": revenue,
        "order_count": order_count,
        "average_order_value": average_order_value,
    }


async def compare_revenue(
    db: AsyncSession,
    organization_id: uuid.UUID,
    period_a_start: date,
    period_a_end: date,
    period_b_start: date,
    period_b_end: date,
) -> dict:
    period_a = await get_revenue_summary(db, organization_id, period_a_start, period_a_end)
    period_b = await get_revenue_summary(db, organization_id, period_b_start, period_b_end)

    if period_b["revenue"] > 0:
        change_pct = (period_a["revenue"] - period_b["revenue"]) / period_b["revenue"] * 100
    else:
        change_pct = None

    return {"period_a": period_a, "period_b": period_b, "change_pct": change_pct}


def _bucket_start(order_date: date, granularity: str) -> date:
    if granularity == "week":
        return order_date - timedelta(days=order_date.weekday())
    if granularity == "month":
        return order_date.replace(day=1)
    return order_date


async def get_revenue_trend(
    db: AsyncSession,
    organization_id: uuid.UUID,
    start_date: date,
    end_date: date,
    granularity: str = "day",
) -> list[dict]:
    start_dt, end_dt = _date_bounds(start_date, end_date)
    stmt = select(Order.ordered_at, Order.total_amount).where(
        Order.organization_id == organization_id,
        Order.status.in_(REVENUE_STATUSES),
        Order.ordered_at >= start_dt,
        Order.ordered_at < end_dt,
    )
    rows = (await db.execute(stmt)).all()

    buckets: dict[date, dict] = {}
    for ordered_at, total_amount in rows:
        bucket_key = _bucket_start(ordered_at.date(), granularity)
        bucket = buckets.setdefault(bucket_key, {"revenue": Decimal("0"), "order_count": 0})
        bucket["revenue"] += total_amount
        bucket["order_count"] += 1

    return [
        {"period_start": period_start, **bucket}
        for period_start, bucket in sorted(buckets.items())
    ]


async def get_top_products(
    db: AsyncSession,
    organization_id: uuid.UUID,
    start_date: date,
    end_date: date,
    limit: int = 5,
) -> list[dict]:
    start_dt, end_dt = _date_bounds(start_date, end_date)
    stmt = (
        select(
            Product.id,
            Product.name,
            Product.category,
            func.sum(OrderItem.subtotal).label("revenue"),
            func.sum(OrderItem.quantity).label("quantity_sold"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.organization_id == organization_id,
            Order.status.in_(REVENUE_STATUSES),
            Order.ordered_at >= start_dt,
            Order.ordered_at < end_dt,
        )
        .group_by(Product.id, Product.name, Product.category)
        .order_by(func.sum(OrderItem.subtotal).desc(), Product.name)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "product_id": product_id,
            "name": name,
            "category": category,
            "revenue": Decimal(str(revenue)),
            "quantity_sold": quantity_sold,
        }
        for product_id, name, category, revenue, quantity_sold in rows
    ]


async def get_customer_metrics(
    db: AsyncSession, organization_id: uuid.UUID, start_date: date, end_date: date
) -> dict:
    start_dt, end_dt = _date_bounds(start_date, end_date)

    total_customers = (
        await db.execute(
            select(func.count()).select_from(Customer).where(
                Customer.organization_id == organization_id
            )
        )
    ).scalar_one()

    new_customers = (
        await db.execute(
            select(func.count())
            .select_from(Customer)
            .where(
                Customer.organization_id == organization_id,
                Customer.created_at >= start_dt,
                Customer.created_at < end_dt,
            )
        )
    ).scalar_one()

    at_risk_customers = (
        await db.execute(
            select(func.count())
            .select_from(Customer)
            .where(
                Customer.organization_id == organization_id,
                Customer.status == CustomerStatus.AT_RISK,
            )
        )
    ).scalar_one()

    active_customers = (
        await db.execute(
            select(func.count(func.distinct(Order.customer_id))).where(
                Order.organization_id == organization_id,
                Order.status.in_(REVENUE_STATUSES),
                Order.ordered_at >= start_dt,
                Order.ordered_at < end_dt,
            )
        )
    ).scalar_one()

    return {
        "total_customers": total_customers,
        "new_customers": new_customers,
        "active_customers": active_customers,
        "at_risk_customers": at_risk_customers,
    }


async def get_at_risk_customers(
    db: AsyncSession, organization_id: uuid.UUID, limit: int = 10
) -> list[Customer]:
    stmt = (
        select(Customer)
        .where(
            Customer.organization_id == organization_id,
            Customer.status == CustomerStatus.AT_RISK,
        )
        .order_by(Customer.lifetime_value.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_order_status_summary(
    db: AsyncSession, organization_id: uuid.UUID, start_date: date, end_date: date
) -> dict:
    start_dt, end_dt = _date_bounds(start_date, end_date)
    stmt = (
        select(Order.status, func.count(Order.id))
        .where(
            Order.organization_id == organization_id,
            Order.ordered_at >= start_dt,
            Order.ordered_at < end_dt,
        )
        .group_by(Order.status)
    )
    rows = (await db.execute(stmt)).all()
    counts = {status.value: 0 for status in OrderStatus}
    for status, count in rows:
        counts[OrderStatus(status).value] = count
    counts["total"] = sum(counts.values())
    return counts
