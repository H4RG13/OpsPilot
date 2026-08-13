import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customers.models import Customer, CustomerStatus
from app.modules.customers.schemas import CustomerCreate, CustomerUpdate
from app.shared.exceptions import NotFoundError
from app.shared.pagination import Page, PageParams


async def create_customer(
    db: AsyncSession, organization_id: uuid.UUID, data: CustomerCreate
) -> Customer:
    customer = Customer(organization_id=organization_id, **data.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


async def get_customer(
    db: AsyncSession, organization_id: uuid.UUID, customer_id: uuid.UUID
) -> Customer:
    stmt = select(Customer).where(
        Customer.id == customer_id, Customer.organization_id == organization_id
    )
    customer = (await db.execute(stmt)).scalar_one_or_none()
    if customer is None:
        raise NotFoundError("Customer was not found.", code="CUSTOMER_NOT_FOUND")
    return customer


async def list_customers(
    db: AsyncSession,
    organization_id: uuid.UUID,
    params: PageParams,
    search: str | None = None,
    status: CustomerStatus | None = None,
) -> Page[Customer]:
    conditions = [Customer.organization_id == organization_id]
    if search:
        like = f"%{search}%"
        conditions.append(or_(Customer.name.ilike(like), Customer.email.ilike(like)))
    if status is not None:
        conditions.append(Customer.status == status)

    count_stmt = select(func.count()).select_from(Customer).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    list_stmt = (
        select(Customer)
        .where(*conditions)
        .order_by(Customer.created_at.desc())
        .offset(params.offset)
        .limit(params.page_size)
    )
    items = list((await db.execute(list_stmt)).scalars().all())

    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


async def update_customer(
    db: AsyncSession, organization_id: uuid.UUID, customer_id: uuid.UUID, data: CustomerUpdate
) -> Customer:
    customer = await get_customer(db, organization_id, customer_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    await db.commit()
    await db.refresh(customer)
    return customer


async def delete_customer(
    db: AsyncSession, organization_id: uuid.UUID, customer_id: uuid.UUID
) -> None:
    customer = await get_customer(db, organization_id, customer_id)
    await db.delete(customer)
    await db.commit()
