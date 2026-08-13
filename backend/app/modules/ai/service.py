import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ai.cost import estimate_cost
from app.modules.ai.models import AIUsage
from app.modules.ai.providers.base import (
    AIProvider,
    PermanentProviderError,
    TransientProviderError,
)
from app.modules.ai.router import ModelRouter, model_router
from app.modules.ai.schemas import AITaskType, AITextResponse, AIToolResponse
from app.shared.exceptions import UpstreamProviderError


class AIService:
    """Domain/API code depends on this, never on a provider SDK directly (spec Section 9)."""

    def __init__(self, provider: AIProvider, router: ModelRouter | None = None):
        self._provider = provider
        self._router = router or model_router

    async def generate_text(
        self,
        db: AsyncSession,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        task_type: AITaskType,
        messages: list[dict[str, str]],
    ) -> AITextResponse:
        return await self._execute_with_fallback(
            db,
            organization_id=organization_id,
            user_id=user_id,
            task_type=task_type,
            call=lambda model: self._provider.generate_text(model=model, messages=messages),
        )

    async def generate_with_tools(
        self,
        db: AsyncSession,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        task_type: AITaskType,
        messages: list[dict[str, str]],
        tools: list[dict],
    ) -> AIToolResponse:
        return await self._execute_with_fallback(
            db,
            organization_id=organization_id,
            user_id=user_id,
            task_type=task_type,
            call=lambda model: self._provider.generate_with_tools(
                model=model, messages=messages, tools=tools
            ),
        )

    async def _execute_with_fallback(
        self,
        db: AsyncSession,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        task_type: AITaskType,
        call: Callable[[str], Awaitable[AITextResponse | AIToolResponse]],
    ) -> AITextResponse | AIToolResponse:
        models = self._router.resolve_chain(task_type)
        last_error: Exception | None = None

        for model in models:
            for _ in range(settings.ai_max_retries_per_model):
                try:
                    response = await call(model)
                except TransientProviderError as exc:
                    last_error = exc
                    continue
                except PermanentProviderError as exc:
                    last_error = exc
                    break
                else:
                    await self._log_usage(db, organization_id, user_id, task_type, response)
                    return response

        raise UpstreamProviderError(
            f"All configured models failed for task '{task_type.value}': {last_error}",
            code="AI_PROVIDER_UNAVAILABLE",
        )

    async def _log_usage(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        task_type: AITaskType,
        response: AITextResponse | AIToolResponse,
    ) -> None:
        cost = estimate_cost(
            response.model, response.usage.input_tokens, response.usage.output_tokens
        )
        db.add(
            AIUsage(
                organization_id=organization_id,
                user_id=user_id,
                provider=response.provider,
                model=response.model,
                task_type=task_type.value,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=response.usage.latency_ms,
                estimated_cost=cost,
            )
        )
        await db.commit()
