import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductUpdate
from app.shared.exceptions import NotFoundError
from app.shared.pagination import Page, PageParams


async def create_product(
    db: AsyncSession, organization_id: uuid.UUID, data: ProductCreate
) -> Product:
    product = Product(organization_id=organization_id, **data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def get_product(
    db: AsyncSession, organization_id: uuid.UUID, product_id: uuid.UUID
) -> Product:
    stmt = select(Product).where(
        Product.id == product_id, Product.organization_id == organization_id
    )
    product = (await db.execute(stmt)).scalar_one_or_none()
    if product is None:
        raise NotFoundError("Product was not found.", code="PRODUCT_NOT_FOUND")
    return product


async def list_products(
    db: AsyncSession,
    organization_id: uuid.UUID,
    params: PageParams,
    category: str | None = None,
    active: bool | None = None,
) -> Page[Product]:
    conditions = [Product.organization_id == organization_id]
    if category:
        conditions.append(Product.category == category)
    if active is not None:
        conditions.append(Product.active == active)

    count_stmt = select(func.count()).select_from(Product).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    list_stmt = (
        select(Product)
        .where(*conditions)
        .order_by(Product.created_at.desc())
        .offset(params.offset)
        .limit(params.page_size)
    )
    items = list((await db.execute(list_stmt)).scalars().all())

    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


async def update_product(
    db: AsyncSession, organization_id: uuid.UUID, product_id: uuid.UUID, data: ProductUpdate
) -> Product:
    product = await get_product(db, organization_id, product_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(
    db: AsyncSession, organization_id: uuid.UUID, product_id: uuid.UUID
) -> None:
    product = await get_product(db, organization_id, product_id)
    await db.delete(product)
    await db.commit()
