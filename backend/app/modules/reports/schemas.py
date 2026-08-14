import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.modules.reports.models import ReportStatus


class ReportResponse(BaseModel):
    id: uuid.UUID
    period_start: date
    period_end: date
    status: ReportStatus
    revenue: Decimal | None
    order_count: int | None
    growth_pct: Decimal | None
    summary: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
