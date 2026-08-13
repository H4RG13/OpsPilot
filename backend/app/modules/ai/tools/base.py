import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class ToolContext:
    """Server-derived context injected into every tool call. Never accepted as an
    LLM-supplied argument (spec Section 10) — organization_id and user_id come from
    the authenticated request, not the model."""

    organization_id: uuid.UUID
    user_id: uuid.UUID
    allow_writes: bool = False


@dataclass(frozen=True)
class ToolDefinition:
    """A tool the Copilot may call. Read tools are safe by default; write tools
    (requires_write_permission=True) are only offered/executed when the caller has
    set ToolContext.allow_writes, and are always logged (spec Section 10)."""

    name: str
    description: str
    args_schema: type[BaseModel]
    handler: Callable[[AsyncSession, ToolContext, BaseModel], Awaitable[Any]]
    requires_write_permission: bool = False

    def to_provider_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema(),
            },
        }


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value
