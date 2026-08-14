import json
import uuid

from app.modules.ai.schemas import AITextResponse, AIUsageInfo
from app.modules.ai.service import AIService
from app.modules.organizations.models import Organization
from app.modules.reports import service as reports_service
from app.modules.reports.models import ReportStatus

STRUCTURED_JSON = json.dumps(
    {
        "answer": "Revenue grew steadily this week.",
        "insights": [{"title": "Strong week", "severity": "low", "evidence": "+10%"}],
        "recommendations": ["Keep it up"],
        "suggested_tasks": [],
    }
)


class FakeTextProvider:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error

    async def generate_text(self, *, model, messages, **kwargs):
        if self._error:
            raise self._error
        return self._response


async def _make_org(db_session) -> uuid.UUID:
    org = Organization(id=uuid.uuid4(), name="Acme")
    db_session.add(org)
    await db_session.commit()
    return org.id


def _text_response() -> AITextResponse:
    return AITextResponse(
        content=STRUCTURED_JSON,
        model="gpt-oss-120b",
        provider="fake",
        usage=AIUsageInfo(input_tokens=15, output_tokens=8, latency_ms=20),
    )


async def test_report_generation_success_populates_fields(db_session):
    org_id = await _make_org(db_session)
    report = await reports_service.create_report(db_session, org_id, None)

    ai_service = AIService(FakeTextProvider(response=_text_response()))
    await reports_service.run_report_generation(db_session, ai_service, report.id)

    refreshed = await reports_service.get_report(db_session, org_id, report.id)
    assert refreshed.status == ReportStatus.COMPLETED
    assert refreshed.revenue is not None
    assert refreshed.order_count == 0
    assert refreshed.completed_at is not None
    assert "Revenue grew steadily" in refreshed.summary


async def test_report_generation_failure_sets_error(db_session):
    org_id = await _make_org(db_session)
    report = await reports_service.create_report(db_session, org_id, None)

    ai_service = AIService(FakeTextProvider(error=RuntimeError("provider exploded")))
    await reports_service.run_report_generation(db_session, ai_service, report.id)

    refreshed = await reports_service.get_report(db_session, org_id, report.id)
    assert refreshed.status == ReportStatus.FAILED
    assert "provider exploded" in refreshed.error_message
