import asyncio
import uuid

from app.core.database import AsyncSessionLocal
from app.modules.ai.dependencies import get_ai_service
from app.modules.reports import service as reports_service
from app.workers.celery_app import celery_app


@celery_app.task(
    name="reports.generate_weekly_report",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def generate_weekly_report(self, report_id: str) -> None:
    try:
        asyncio.run(_generate_weekly_report_async(report_id))
    except Exception as exc:  # pragma: no cover - exercised via retry, not unit tests
        raise self.retry(exc=exc) from exc


async def _generate_weekly_report_async(report_id: str) -> None:
    async with AsyncSessionLocal() as db:
        await reports_service.run_report_generation(db, get_ai_service(), uuid.UUID(report_id))
