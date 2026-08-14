from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tasks.models import Task, TaskPriority, TaskStatus
from app.modules.tasks.schemas import TaskCreate, TaskUpdate
from app.shared.exceptions import NotFoundError
from app.shared.pagination import Page, PageParams


async def create_task(
    db: AsyncSession, organization_id: uuid.UUID, created_by: uuid.UUID | None, data: TaskCreate
) -> Task:
    task = Task(organization_id=organization_id, created_by=created_by, **data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, organization_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    stmt = select(Task).where(Task.id == task_id, Task.organization_id == organization_id)
    task = (await db.execute(stmt)).scalar_one_or_none()
    if task is None:
        raise NotFoundError("Task was not found.", code="TASK_NOT_FOUND")
    return task


async def list_tasks(
    db: AsyncSession,
    organization_id: uuid.UUID,
    params: PageParams,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
) -> Page[Task]:
    conditions = [Task.organization_id == organization_id]
    if status is not None:
        conditions.append(Task.status == status)
    if priority is not None:
        conditions.append(Task.priority == priority)

    count_stmt = select(func.count()).select_from(Task).where(*conditions)
    total = (await db.execute(count_stmt)).scalar_one()

    list_stmt = (
        select(Task)
        .where(*conditions)
        .order_by(Task.created_at.desc())
        .offset(params.offset)
        .limit(params.page_size)
    )
    items = list((await db.execute(list_stmt)).scalars().all())

    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


async def update_task(
    db: AsyncSession, organization_id: uuid.UUID, task_id: uuid.UUID, data: TaskUpdate
) -> Task:
    task = await get_task(db, organization_id, task_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task
