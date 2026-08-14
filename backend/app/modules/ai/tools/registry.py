from typing import Any

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.tools.base import ToolContext, ToolDefinition, to_jsonable
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
from app.modules.ai.tools.task_tools import CREATE_TASK, LIST_OPEN_TASKS
from app.shared.exceptions import AuthorizationError, ValidationAppError

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
        LIST_OPEN_TASKS,
        CREATE_TASK,
    ]
}


def get_tool_schemas(allow_writes: bool = False) -> list[dict]:
    return [
        tool.to_provider_schema()
        for tool in TOOL_REGISTRY.values()
        if allow_writes or not tool.requires_write_permission
    ]


async def execute_tool(db: AsyncSession, ctx: ToolContext, name: str, raw_arguments: dict) -> Any:
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        raise ValidationAppError(f"Unknown tool '{name}'.", code="UNKNOWN_TOOL")

    if tool.requires_write_permission and not ctx.allow_writes:
        raise AuthorizationError(
            f"Tool '{name}' requires explicit write permission for this message.",
            code="AI_WRITE_NOT_PERMITTED",
        )

    try:
        args = tool.args_schema.model_validate(raw_arguments)
    except PydanticValidationError as exc:
        raise ValidationAppError(
            f"Invalid arguments for tool '{name}': {exc}", code="INVALID_TOOL_ARGUMENTS"
        ) from exc

    result = await tool.handler(db, ctx, args)
    return to_jsonable(result)
