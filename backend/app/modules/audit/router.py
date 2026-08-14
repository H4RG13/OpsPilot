from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.audit import service
from app.modules.audit.schemas import AuditLogResponse, audit_log_to_response
from app.modules.auth.dependencies import AuthContext, require_role
from app.shared.pagination import Page, PageParams
from app.shared.permissions import Role

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=Page[AuditLogResponse])
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> Page:
    params = PageParams(page=page, page_size=page_size)
    result = await service.list_audit_logs(db, context.organization_id, params)
    return Page(
        items=[audit_log_to_response(entry) for entry in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )
