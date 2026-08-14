import uuid
from collections.abc import Callable

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.auth.dependencies import AuthContext, get_current_context
from app.modules.reports import service
from app.modules.reports.dependencies import get_report_dispatcher
from app.modules.reports.schemas import ReportResponse
from app.shared.pagination import Page, PageParams

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=Page[ReportResponse])
async def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> Page:
    params = PageParams(page=page, page_size=page_size)
    return await service.list_reports(db, context.organization_id, params)


@router.post(
    "/generate",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            rate_limit(
                "report_generate", settings.ai_report_rate_limit_per_hour, window_seconds=3600
            )
        )
    ],
)
async def generate_report(
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
    dispatch: Callable[[uuid.UUID], None] = Depends(get_report_dispatcher),
) -> ReportResponse:
    report = await service.create_report(db, context.organization_id, context.user.id)
    dispatch(report.id)
    return ReportResponse.model_validate(report)
