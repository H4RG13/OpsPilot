import uuid

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.modules.ai.models import AIUsage
from app.modules.ai.providers.base import PermanentProviderError, TransientProviderError
from app.modules.ai.router import ModelRouter
from app.modules.ai.schemas import AITaskType, AITextResponse, AIUsageInfo
from app.modules.ai.service import AIService
from app.modules.organizations.models import Organization
from app.shared.exceptions import UpstreamProviderError


def _response(model: str) -> AITextResponse:
    return AITextResponse(
        content="hello",
        model=model,
        provider="fake",
        usage=AIUsageInfo(input_tokens=10, output_tokens=5, latency_ms=42),
    )


class FakeProvider:
    def __init__(self, outcomes: dict[str, list]):
        self._outcomes = outcomes
        self.calls: list[str] = []

    async def generate_text(self, *, model: str, messages, **kwargs):
        self.calls.append(model)
        outcome = self._outcomes[model].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


async def _make_org(db_session) -> uuid.UUID:
    org = Organization(id=uuid.uuid4(), name="Acme")
    db_session.add(org)
    await db_session.commit()
    return org.id


async def test_succeeds_on_first_call_and_logs_usage(db_session):
    org_id = await _make_org(db_session)
    provider = FakeProvider({settings.ai_default_model: [_response(settings.ai_default_model)]})
    service = AIService(provider)

    response = await service.generate_text(
        db_session,
        organization_id=org_id,
        user_id=None,
        task_type=AITaskType.SUMMARY,
        messages=[{"role": "user", "content": "hi"}],
    )

    assert response.content == "hello"
    assert provider.calls == [settings.ai_default_model]

    usage_rows = (await db_session.execute(select(AIUsage))).scalars().all()
    assert len(usage_rows) == 1
    assert usage_rows[0].model == settings.ai_default_model
    assert usage_rows[0].task_type == AITaskType.SUMMARY.value


async def test_retries_transient_failure_before_succeeding(db_session):
    org_id = await _make_org(db_session)
    provider = FakeProvider(
        {
            settings.ai_default_model: [
                TransientProviderError("timeout"),
                _response(settings.ai_default_model),
            ]
        }
    )
    service = AIService(provider)

    response = await service.generate_text(
        db_session,
        organization_id=org_id,
        user_id=None,
        task_type=AITaskType.SUMMARY,
        messages=[{"role": "user", "content": "hi"}],
    )

    assert response.content == "hello"
    assert provider.calls == [settings.ai_default_model, settings.ai_default_model]


async def test_falls_back_to_next_model_after_exhausting_retries(db_session):
    org_id = await _make_org(db_session)
    provider = FakeProvider(
        {
            settings.ai_default_model: [
                TransientProviderError("timeout"),
                TransientProviderError("timeout"),
            ],
            settings.ai_reasoning_model: [_response(settings.ai_reasoning_model)],
        }
    )
    service = AIService(provider)

    response = await service.generate_text(
        db_session,
        organization_id=org_id,
        user_id=None,
        task_type=AITaskType.SUMMARY,
        messages=[{"role": "user", "content": "hi"}],
    )

    assert response.model == settings.ai_reasoning_model
    assert provider.calls == [
        settings.ai_default_model,
        settings.ai_default_model,
        settings.ai_reasoning_model,
    ]


async def test_permanent_error_skips_remaining_retries_and_falls_back(db_session):
    org_id = await _make_org(db_session)
    provider = FakeProvider(
        {
            settings.ai_default_model: [PermanentProviderError("bad request")],
            settings.ai_reasoning_model: [_response(settings.ai_reasoning_model)],
        }
    )
    service = AIService(provider)

    response = await service.generate_text(
        db_session,
        organization_id=org_id,
        user_id=None,
        task_type=AITaskType.SUMMARY,
        messages=[{"role": "user", "content": "hi"}],
    )

    assert response.model == settings.ai_reasoning_model
    # only one call to the default model — the permanent error was not retried
    assert provider.calls == [settings.ai_default_model, settings.ai_reasoning_model]


async def test_all_models_failing_raises_upstream_provider_error(db_session):
    org_id = await _make_org(db_session)
    provider = FakeProvider(
        {
            settings.ai_default_model: [
                TransientProviderError("timeout"),
                TransientProviderError("timeout"),
            ],
            settings.ai_reasoning_model: [
                TransientProviderError("timeout"),
                TransientProviderError("timeout"),
            ],
        }
    )
    service = AIService(provider)

    with pytest.raises(UpstreamProviderError) as exc_info:
        await service.generate_text(
            db_session,
            organization_id=org_id,
            user_id=None,
            task_type=AITaskType.SUMMARY,
            messages=[{"role": "user", "content": "hi"}],
        )

    assert exc_info.value.code == "AI_PROVIDER_UNAVAILABLE"

    usage_rows = (await db_session.execute(select(AIUsage))).scalars().all()
    assert len(usage_rows) == 0


async def test_custom_router_is_respected(db_session):
    org_id = await _make_org(db_session)
    provider = FakeProvider({"custom-model": [_response("custom-model")]})
    router = ModelRouter({AITaskType.SUMMARY: "custom-model"})
    service = AIService(provider, router=router)

    response = await service.generate_text(
        db_session,
        organization_id=org_id,
        user_id=None,
        task_type=AITaskType.SUMMARY,
        messages=[{"role": "user", "content": "hi"}],
    )
    assert response.model == "custom-model"
