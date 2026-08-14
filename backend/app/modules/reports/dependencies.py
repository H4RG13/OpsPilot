import uuid
from collections.abc import Callable

from app.modules.reports.tasks import generate_weekly_report


def get_report_dispatcher() -> Callable[[uuid.UUID], None]:
    def _dispatch(report_id: uuid.UUID) -> None:
        generate_weekly_report.delay(str(report_id))

    return _dispatch
