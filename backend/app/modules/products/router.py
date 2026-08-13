import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, get_current_context, require_role
from app.modules.products import service
from app.modules.products.schemas import ProductCreate, ProductResponse, ProductUpdate
from app.shared.pagination import Page, PageParams
from app.shared.permissions import Role

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=Page[ProductResponse])
async def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> Page:
    params = PageParams(page=page, page_size=page_size)
    return await service.list_products(
        db, context.organization_id, params, category=category, active=active
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    product = await service.create_product(db, context.organization_id, data)
    return ProductResponse.model_validate(product)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    product = await service.get_product(db, context.organization_id, product_id)
    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    product = await service.update_product(db, context.organization_id, product_id, data)
    return ProductResponse.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: uuid.UUID,
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.delete_product(db, context.organization_id, product_id)
