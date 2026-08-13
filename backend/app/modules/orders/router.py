import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, get_current_context, require_role
from app.modules.orders import service
from app.modules.orders.models import OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderResponse, OrderStatusUpdate
from app.shared.pagination import Page, PageParams
from app.shared.permissions import Role

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=Page[OrderResponse])
async def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> Page:
    params = PageParams(page=page, page_size=page_size)
    return await service.list_orders(db, context.organization_id, params, status=status_filter)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    order = await service.create_order(db, context.organization_id, data)
    return OrderResponse.model_validate(order)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    order = await service.get_order(db, context.organization_id, order_id)
    return OrderResponse.model_validate(order)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order_status(
    order_id: uuid.UUID,
    data: OrderStatusUpdate,
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    order = await service.update_order_status(db, context.organization_id, order_id, data.status)
    return OrderResponse.model_validate(order)
