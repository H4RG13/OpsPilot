import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.parsing import parse_structured_answer
from app.modules.ai.schemas import AITaskType
from app.modules.ai.service import AIService
from app.modules.analytics import service as analytics_service
from app.modules.reports.models import Report, ReportStatus
from app.shared.exceptions import NotFoundError
from app.shared.pagination import Page, PageParams

REPORT_WINDOW_DAYS = 7

REPORT_SYSTEM_PROMPT = (
    "You are an AI Operations Copilot generating a weekly business report. "
    "Given the revenue, order count, and growth percentage for the period, "
    "respond ONLY with a JSON object of this exact shape: "
    '{"answer": string, '
    '"insights": [{"title": string, "severity": "low"|"medium"|"high", "evidence": string}], '
    '"recommendations": [string], '
    '"suggested_tasks": [{"title": string, "priority": "low"|"medium"|"high"}]}'
)


async def create_report(
    db: AsyncSession, organization_id: uuid.UUID, generated_by: uuid.UUID | None
) -> Report:
    period_end = date.today()
    period_start = period_end - timedelta(days=REPORT_WINDOW_DAYS - 1)

    report = Report(
        organization_id=organization_id,
        generated_by=generated_by,
        period_start=period_start,
        period_end=period_end,
        status=ReportStatus.QUEUED,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def get_report(db: AsyncSession, organization_id: uuid.UUID, report_id: uuid.UUID) -> Report:
    stmt = select(Report).where(Report.id == report_id, Report.organization_id == organization_id)
    report = (await db.execute(stmt)).scalar_one_or_none()
    if report is None:
        raise NotFoundError("Report was not found.", code="REPORT_NOT_FOUND")
    return report


async def list_reports(
    db: AsyncSession, organization_id: uuid.UUID, params: PageParams
) -> Page[Report]:
    conditions = (Report.organization_id == organization_id,)

    total = (
        await db.execute(select(func.count()).select_from(Report).where(*conditions))
    ).scalar_one()

    items = list(
        (
            await db.execute(
                select(Report)
                .where(*conditions)
                .order_by(Report.created_at.desc())
                .offset(params.offset)
                .limit(params.page_size)
            )
        )
        .scalars()
        .all()
    )

    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


async def run_report_generation(
    db: AsyncSession, ai_service: AIService, report_id: uuid.UUID
) -> None:
    """The testable core of weekly report generation — takes a db session and
    AIService directly so it can run without Celery or a live provider. The
    Celery task in tasks.py is a thin wrapper that supplies both for real."""
    report = await db.get(Report, report_id)
    if report is None:
        return

    report.status = ReportStatus.RUNNING
    await db.commit()

    try:
        summary = await analytics_service.get_revenue_summary(
            db, report.organization_id, report.period_start, report.period_end
        )

        window_days = (report.period_end - report.period_start).days + 1
        previous_end = report.period_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=window_days - 1)
        comparison = await analytics_service.compare_revenue(
            db,
            report.organization_id,
            report.period_start,
            report.period_end,
            previous_start,
            previous_end,
        )

        messages = [
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Revenue: {summary['revenue']}, Orders: {summary['order_count']}, "
                    f"Growth vs. previous period: {comparison['change_pct']}%."
                ),
            },
        ]
        ai_response = await ai_service.generate_text(
            db,
            organization_id=report.organization_id,
            user_id=report.generated_by,
            task_type=AITaskType.BUSINESS_ANALYSIS,
            messages=messages,
        )
        structured = parse_structured_answer(ai_response.content)

        report.revenue = summary["revenue"]
        report.order_count = summary["order_count"]
        report.growth_pct = comparison["change_pct"]
        report.summary = structured.model_dump_json()
        report.status = ReportStatus.COMPLETED
        report.completed_at = datetime.now(UTC)
    except Exception as exc:
        report.status = ReportStatus.FAILED
        report.error_message = str(exc)

    await db.commit()
