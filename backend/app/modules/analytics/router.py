from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.analytics import service
from app.modules.analytics.schemas import (
    CustomerMetricsResponse,
    OverviewResponse,
    ProductsPerformanceResponse,
    RevenueTrendResponse,
)
from app.modules.auth.dependencies import AuthContext, get_current_context
from app.shared.exceptions import ValidationAppError

router = APIRouter(prefix="/analytics", tags=["analytics"])

DEFAULT_WINDOW_DAYS = 30


def _resolve_range(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    resolved_end = end_date or date.today()
    resolved_start = start_date or (resolved_end - timedelta(days=DEFAULT_WINDOW_DAYS - 1))
    if resolved_start > resolved_end:
        raise ValidationAppError(
            "start_date must not be after end_date.", code="INVALID_DATE_RANGE"
        )
    return resolved_start, resolved_end


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> OverviewResponse:
    resolved_start, resolved_end = _resolve_range(start_date, end_date)

    revenue_summary = await service.get_revenue_summary(
        db, context.organization_id, resolved_start, resolved_end
    )
    customer_metrics = await service.get_customer_metrics(
        db, context.organization_id, resolved_start, resolved_end
    )

    return OverviewResponse(
        start_date=resolved_start,
        end_date=resolved_end,
        revenue=revenue_summary["revenue"],
        order_count=revenue_summary["order_count"],
        average_order_value=revenue_summary["average_order_value"],
        total_customers=customer_metrics["total_customers"],
        active_customers=customer_metrics["active_customers"],
    )


@router.get("/revenue", response_model=RevenueTrendResponse)
async def get_revenue_trend(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    granularity: str = Query(default="day", pattern="^(day|week|month)$"),
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> RevenueTrendResponse:
    resolved_start, resolved_end = _resolve_range(start_date, end_date)

    points = await service.get_revenue_trend(
        db, context.organization_id, resolved_start, resolved_end, granularity
    )

    return RevenueTrendResponse(
        start_date=resolved_start,
        end_date=resolved_end,
        granularity=granularity,
        points=points,
    )


@router.get("/products", response_model=ProductsPerformanceResponse)
async def get_product_performance(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=50),
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> ProductsPerformanceResponse:
    resolved_start, resolved_end = _resolve_range(start_date, end_date)

    products = await service.get_top_products(
        db, context.organization_id, resolved_start, resolved_end, limit
    )

    return ProductsPerformanceResponse(
        start_date=resolved_start, end_date=resolved_end, products=products
    )


@router.get("/customers", response_model=CustomerMetricsResponse)
async def get_customer_metrics(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> CustomerMetricsResponse:
    resolved_start, resolved_end = _resolve_range(start_date, end_date)

    metrics = await service.get_customer_metrics(
        db, context.organization_id, resolved_start, resolved_end
    )

    return CustomerMetricsResponse(start_date=resolved_start, end_date=resolved_end, **metrics)
