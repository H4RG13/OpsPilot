import asyncio
import uuid

from app.core.database import AsyncSessionLocal, engine
from app.modules.imports import service as imports_service
from app.workers.celery_app import celery_app


@celery_app.task(
    name="imports.run_import_job",
    bind=True,
    max_retries=1,
    default_retry_delay=15,
)
def run_import_job(self, job_id: str) -> None:
    try:
        asyncio.run(_run_import_job_async(job_id))
    except Exception as exc:  # pragma: no cover - exercised via retry, not unit tests
        raise self.retry(exc=exc) from exc


async def _run_import_job_async(job_id: str) -> None:
    try:
        async with AsyncSessionLocal() as db:
            await imports_service.run_import_job(db, uuid.UUID(job_id))
    finally:
        # asyncpg connections are bound to the event loop that created them, but
        # `asyncio.run()` gives each task invocation its own loop while `engine`
        # is a module-level singleton shared across tasks in this worker process.
        # Dispose the pool now so the next task's loop opens fresh connections
        # instead of reusing ones tied to this (about to close) loop.
        await engine.dispose()
