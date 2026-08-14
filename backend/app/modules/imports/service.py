import csv
import io
import json
import uuid
from datetime import UTC, datetime

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customers.models import Customer
from app.modules.customers.schemas import CustomerCreate
from app.modules.imports.models import ImportJob, ImportStatus, ImportType
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate
from app.shared.exceptions import NotFoundError, ValidationAppError

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
MAX_REPORTED_ERRORS = 50

REQUIRED_COLUMNS: dict[ImportType, set[str]] = {
    ImportType.CUSTOMERS: {"name", "email"},
    ImportType.PRODUCTS: {"name", "category", "price"},
}


async def create_import_job(
    db: AsyncSession,
    organization_id: uuid.UUID,
    created_by: uuid.UUID | None,
    import_type: ImportType,
    filename: str,
    raw_content: str,
) -> ImportJob:
    if not filename.lower().endswith(".csv"):
        raise ValidationAppError("Only .csv files are supported.", code="INVALID_FILE_TYPE")
    if len(raw_content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
        raise ValidationAppError(
            "File exceeds the 5MB import size limit.", code="FILE_TOO_LARGE"
        )

    job = ImportJob(
        organization_id=organization_id,
        created_by=created_by,
        import_type=import_type,
        status=ImportStatus.QUEUED,
        filename=filename,
        raw_content=raw_content,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_import_job(
    db: AsyncSession, organization_id: uuid.UUID, job_id: uuid.UUID
) -> ImportJob:
    stmt = select(ImportJob).where(
        ImportJob.id == job_id, ImportJob.organization_id == organization_id
    )
    job = (await db.execute(stmt)).scalar_one_or_none()
    if job is None:
        raise NotFoundError("Import job was not found.", code="IMPORT_JOB_NOT_FOUND")
    return job


def _clean_row(row: dict) -> dict:
    """Strip whitespace and drop blank cells so optional fields fall back to
    their schema default instead of failing validation on an empty string."""
    return {
        key: value.strip()
        for key, value in row.items()
        if key is not None and isinstance(value, str) and value.strip() != ""
    }


async def _upsert_customer(db: AsyncSession, organization_id: uuid.UUID, row: dict) -> None:
    data = CustomerCreate.model_validate(_clean_row(row))
    stmt = select(Customer).where(
        Customer.organization_id == organization_id, Customer.email == data.email
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        for field, value in data.model_dump().items():
            setattr(existing, field, value)
    else:
        db.add(Customer(organization_id=organization_id, **data.model_dump()))
    await db.flush()


async def _upsert_product(db: AsyncSession, organization_id: uuid.UUID, row: dict) -> None:
    data = ProductCreate.model_validate(_clean_row(row))
    stmt = select(Product).where(
        Product.organization_id == organization_id, Product.name == data.name
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        for field, value in data.model_dump().items():
            setattr(existing, field, value)
    else:
        db.add(Product(organization_id=organization_id, **data.model_dump()))
    await db.flush()


_UPSERT_HANDLERS = {
    ImportType.CUSTOMERS: _upsert_customer,
    ImportType.PRODUCTS: _upsert_product,
}


async def _fail_job(db: AsyncSession, job: ImportJob, message: str) -> None:
    job.status = ImportStatus.FAILED
    job.errors = json.dumps([{"row": 0, "message": message}])
    job.completed_at = datetime.now(UTC)
    await db.commit()


async def run_import_job(db: AsyncSession, job_id: uuid.UUID) -> None:
    """The testable core of CSV import processing — takes a db session
    directly so it can run without Celery. The Celery task in tasks.py is a
    thin wrapper that supplies a fresh session for real."""
    job = await db.get(ImportJob, job_id)
    if job is None:
        return

    job.status = ImportStatus.RUNNING
    await db.commit()

    try:
        import_type = ImportType(job.import_type)
        reader = csv.DictReader(io.StringIO(job.raw_content))
        headers = {h.strip() for h in (reader.fieldnames or []) if h}
        missing = REQUIRED_COLUMNS[import_type] - headers
        if missing:
            raise ValueError(f"CSV is missing required column(s): {', '.join(sorted(missing))}")
        rows = list(reader)
    except Exception as exc:
        await _fail_job(db, job, str(exc))
        return

    job.total_rows = len(rows)

    upsert = _UPSERT_HANDLERS[import_type]
    errors: list[dict] = []
    imported = 0

    for line_number, row in enumerate(rows, start=2):
        try:
            # A SAVEPOINT, not a full rollback: a bad row only undoes its own
            # pending write, leaving every already-imported row in this job
            # — and the `job` object itself — untouched and un-expired.
            async with db.begin_nested():
                await upsert(db, job.organization_id, row)
            imported += 1
        except (PydanticValidationError, ValueError) as exc:
            if len(errors) < MAX_REPORTED_ERRORS:
                errors.append({"row": line_number, "message": str(exc)})

    job.imported_rows = imported
    job.failed_rows = len(rows) - imported
    job.errors = json.dumps(errors)
    job.status = ImportStatus.COMPLETED
    job.completed_at = datetime.now(UTC)
    await db.commit()
