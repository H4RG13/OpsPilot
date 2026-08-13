import uuid
from typing import Any

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.tools.base import ToolDefinition, to_jsonable
from app.modules.ai.tools.customer_tools import (
    GET_AT_RISK_CUSTOMERS,
    GET_CUSTOMER_METRICS,
    SEARCH_CUSTOMERS,
)
from app.modules.ai.tools.product_tools import GET_TOP_PRODUCTS
from app.modules.ai.tools.revenue_tools import (
    COMPARE_REVENUE,
    GET_ORDER_SUMMARY,
    GET_REVENUE_SUMMARY,
)
from app.shared.exceptions import ValidationAppError

# create_task/list_open_tasks are deferred to Phase 6 (Automation) — the
# Tasks module those tools depend on doesn't exist yet. See PLAN.md.
TOOL_REGISTRY: dict[str, ToolDefinition] = {
    tool.name: tool
    for tool in [
        GET_REVENUE_SUMMARY,
        COMPARE_REVENUE,
        GET_ORDER_SUMMARY,
        GET_TOP_PRODUCTS,
        GET_CUSTOMER_METRICS,
        GET_AT_RISK_CUSTOMERS,
        SEARCH_CUSTOMERS,
    ]
}


def get_tool_schemas() -> list[dict]:
    return [tool.to_provider_schema() for tool in TOOL_REGISTRY.values()]


async def execute_tool(
    db: AsyncSession, organization_id: uuid.UUID, name: str, raw_arguments: dict
) -> Any:
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        raise ValidationAppError(f"Unknown tool '{name}'.", code="UNKNOWN_TOOL")

    try:
        args = tool.args_schema.model_validate(raw_arguments)
    except PydanticValidationError as exc:
        raise ValidationAppError(
            f"Invalid arguments for tool '{name}': {exc}", code="INVALID_TOOL_ARGUMENTS"
        ) from exc

    result = await tool.handler(db, organization_id, args)
    return to_jsonable(result)
