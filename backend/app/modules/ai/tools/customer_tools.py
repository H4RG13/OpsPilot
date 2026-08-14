from datetime import date

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.tools.base import ToolContext, ToolDefinition
from app.modules.analytics import service as analytics_service
from app.modules.customers import service as customers_service
from app.shared.pagination import PageParams


class CustomerMetricsArgs(BaseModel):
    start_date: date
    end_date: date


async def _get_customer_metrics(db: AsyncSession, ctx: ToolContext, args: BaseModel):
    assert isinstance(args, CustomerMetricsArgs)
    return await analytics_service.get_customer_metrics(
        db, ctx.organization_id, args.start_date, args.end_date
    )


GET_CUSTOMER_METRICS = ToolDefinition(
    name="get_customer_metrics",
    description="Get total/new/active/at-risk customer counts for a date range.",
    args_schema=CustomerMetricsArgs,
    handler=_get_customer_metrics,
)


class AtRiskCustomersArgs(BaseModel):
    limit: int = Field(default=10, ge=1, le=50)


async def _get_at_risk_customers(db: AsyncSession, ctx: ToolContext, args: BaseModel):
    assert isinstance(args, AtRiskCustomersArgs)
    customers = await analytics_service.get_at_risk_customers(db, ctx.organization_id, args.limit)
    return [
        {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "lifetime_value": c.lifetime_value,
        }
        for c in customers
    ]


GET_AT_RISK_CUSTOMERS = ToolDefinition(
    name="get_at_risk_customers",
    description="Get customers flagged as at-risk, ordered by lifetime value.",
    args_schema=AtRiskCustomersArgs,
    handler=_get_at_risk_customers,
)


class SearchCustomersArgs(BaseModel):
    query: str = Field(min_length=1, max_length=255)
    limit: int = Field(default=10, ge=1, le=50)


async def _search_customers(db: AsyncSession, ctx: ToolContext, args: BaseModel):
    assert isinstance(args, SearchCustomersArgs)
    page = await customers_service.list_customers(
        db,
        ctx.organization_id,
        PageParams(page=1, page_size=args.limit),
        search=args.query,
    )
    return [
        {"id": c.id, "name": c.name, "email": c.email, "status": c.status} for c in page.items
    ]


SEARCH_CUSTOMERS = ToolDefinition(
    name="search_customers",
    description="Search customers by name or email.",
    args_schema=SearchCustomersArgs,
    handler=_search_customers,
)
