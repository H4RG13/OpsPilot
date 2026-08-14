import json
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.imports.models import ImportJob, ImportStatus, ImportType


class ImportRowError(BaseModel):
    row: int
    message: str


class ImportJobResponse(BaseModel):
    id: uuid.UUID
    import_type: ImportType
    status: ImportStatus
    filename: str
    total_rows: int | None
    imported_rows: int | None
    failed_rows: int | None
    errors: list[ImportRowError]
    created_at: datetime
    completed_at: datetime | None


def import_job_to_response(job: ImportJob) -> ImportJobResponse:
    raw_errors = json.loads(job.errors) if job.errors else []
    return ImportJobResponse(
        id=job.id,
        import_type=job.import_type,
        status=job.status,
        filename=job.filename,
        total_rows=job.total_rows,
        imported_rows=job.imported_rows,
        failed_rows=job.failed_rows,
        errors=[ImportRowError(**e) for e in raw_errors],
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
