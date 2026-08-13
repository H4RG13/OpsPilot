import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, get_current_context, require_role
from app.modules.customers import service
from app.modules.customers.models import CustomerStatus
from app.modules.customers.schemas import CustomerCreate, CustomerResponse, CustomerUpdate
from app.shared.pagination import Page, PageParams
from app.shared.permissions import Role

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=Page[CustomerResponse])
async def list_customers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    status_filter: CustomerStatus | None = Query(default=None, alias="status"),
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> Page:
    params = PageParams(page=page, page_size=page_size)
    return await service.list_customers(
        db, context.organization_id, params, search=search, status=status_filter
    )


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    customer = await service.create_customer(db, context.organization_id, data)
    return CustomerResponse.model_validate(customer)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    customer = await service.get_customer(db, context.organization_id, customer_id)
    return CustomerResponse.model_validate(customer)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    customer = await service.update_customer(db, context.organization_id, customer_id, data)
    return CustomerResponse.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: uuid.UUID,
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.delete_customer(db, context.organization_id, customer_id)
