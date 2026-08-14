from __future__ import annotations

import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.shared.pagination import Page, PageParams


async def log_action(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            event_metadata=json.dumps(metadata) if metadata else None,
        )
    )
    await db.commit()


async def list_audit_logs(
    db: AsyncSession, organization_id: uuid.UUID, params: PageParams
) -> Page[AuditLog]:
    conditions = (AuditLog.organization_id == organization_id,)

    total = (
        await db.execute(select(func.count()).select_from(AuditLog).where(*conditions))
    ).scalar_one()

    items = list(
        (
            await db.execute(
                select(AuditLog)
                .where(*conditions)
                .order_by(AuditLog.created_at.desc())
                .offset(params.offset)
                .limit(params.page_size)
            )
        )
        .scalars()
        .all()
    )

    return Page(items=items, total=total, page=params.page, page_size=params.page_size)
