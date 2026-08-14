from datetime import date

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.tools.base import ToolContext, ToolDefinition
from app.modules.analytics import service as analytics_service


class RevenueSummaryArgs(BaseModel):
    start_date: date
    end_date: date


async def _get_revenue_summary(db: AsyncSession, ctx: ToolContext, args: BaseModel):
    assert isinstance(args, RevenueSummaryArgs)
    return await analytics_service.get_revenue_summary(
        db, ctx.organization_id, args.start_date, args.end_date
    )


GET_REVENUE_SUMMARY = ToolDefinition(
    name="get_revenue_summary",
    description="Get total revenue, order count, and average order value for a date range.",
    args_schema=RevenueSummaryArgs,
    handler=_get_revenue_summary,
)


class CompareRevenueArgs(BaseModel):
    period_a_start: date
    period_a_end: date
    period_b_start: date
    period_b_end: date


async def _compare_revenue(db: AsyncSession, ctx: ToolContext, args: BaseModel):
    assert isinstance(args, CompareRevenueArgs)
    return await analytics_service.compare_revenue(
        db,
        ctx.organization_id,
        args.period_a_start,
        args.period_a_end,
        args.period_b_start,
        args.period_b_end,
    )


COMPARE_REVENUE = ToolDefinition(
    name="compare_revenue",
    description="Compare revenue between two date ranges (e.g. this month vs. last month).",
    args_schema=CompareRevenueArgs,
    handler=_compare_revenue,
)


class OrderSummaryArgs(BaseModel):
    start_date: date
    end_date: date


async def _get_order_summary(db: AsyncSession, ctx: ToolContext, args: BaseModel):
    assert isinstance(args, OrderSummaryArgs)
    return await analytics_service.get_order_status_summary(
        db, ctx.organization_id, args.start_date, args.end_date
    )


GET_ORDER_SUMMARY = ToolDefinition(
    name="get_order_summary",
    description="Get order counts broken down by status (pending/completed/cancelled).",
    args_schema=OrderSummaryArgs,
    handler=_get_order_summary,
)
