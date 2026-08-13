from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.ai.models import AIUsage
from app.modules.ai.schemas import AIUsageRecordResponse
from app.modules.auth.dependencies import AuthContext, require_role
from app.shared.pagination import Page, PageParams
from app.shared.permissions import Role

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/usage", response_model=Page[AIUsageRecordResponse])
async def list_ai_usage(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> Page:
    params = PageParams(page=page, page_size=page_size)

    count_stmt = (
        select(func.count())
        .select_from(AIUsage)
        .where(AIUsage.organization_id == context.organization_id)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    list_stmt = (
        select(AIUsage)
        .where(AIUsage.organization_id == context.organization_id)
        .order_by(AIUsage.created_at.desc())
        .offset(params.offset)
        .limit(params.page_size)
    )
    items = list((await db.execute(list_stmt)).scalars().all())

    return Page(items=items, total=total, page=params.page, page_size=params.page_size)
