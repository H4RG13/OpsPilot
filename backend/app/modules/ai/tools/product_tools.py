from datetime import date

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.tools.base import ToolContext, ToolDefinition
from app.modules.analytics import service as analytics_service


class TopProductsArgs(BaseModel):
    start_date: date
    end_date: date
    limit: int = Field(default=5, ge=1, le=50)


async def _get_top_products(db: AsyncSession, ctx: ToolContext, args: BaseModel):
    assert isinstance(args, TopProductsArgs)
    return await analytics_service.get_top_products(
        db, ctx.organization_id, args.start_date, args.end_date, args.limit
    )


GET_TOP_PRODUCTS = ToolDefinition(
    name="get_top_products",
    description="Get the top-selling products by revenue for a date range.",
    args_schema=TopProductsArgs,
    handler=_get_top_products,
)
