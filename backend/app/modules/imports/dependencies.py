import uuid
from collections.abc import Callable

from app.modules.imports.tasks import run_import_job


def get_import_dispatcher() -> Callable[[uuid.UUID], None]:
    def _dispatch(job_id: uuid.UUID) -> None:
        run_import_job.delay(str(job_id))

    return _dispatch
