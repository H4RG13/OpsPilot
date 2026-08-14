from datetime import date

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.tools.base import ToolContext, ToolDefinition
from app.modules.audit import service as audit_service
from app.modules.tasks.models import Task, TaskPriority, TaskStatus


class CreateTaskArgs(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None


async def _create_task(db: AsyncSession, ctx: ToolContext, args: BaseModel):
    assert isinstance(args, CreateTaskArgs)

    # ctx.allow_writes is already enforced by the registry before this handler
    # runs; requires_write_permission=True below is what triggers that check.
    task = Task(
        organization_id=ctx.organization_id,
        created_by=ctx.user_id,
        title=args.title,
        description=args.description,
        priority=args.priority,
        due_date=args.due_date,
        status=TaskStatus.OPEN,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    await audit_service.log_action(
        db,
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="ai.task_created",
        entity_type="task",
        entity_id=task.id,
        metadata={"title": task.title},
    )

    return {"created": True, "task_id": task.id, "title": task.title}


CREATE_TASK = ToolDefinition(
    name="create_task",
    description="Create a task in the organization's task list. Requires explicit user permission.",
    args_schema=CreateTaskArgs,
    handler=_create_task,
    requires_write_permission=True,
)


class ListOpenTasksArgs(BaseModel):
    limit: int = Field(default=10, ge=1, le=50)


async def _list_open_tasks(db: AsyncSession, ctx: ToolContext, args: BaseModel):
    assert isinstance(args, ListOpenTasksArgs)
    stmt = (
        select(Task)
        .where(Task.organization_id == ctx.organization_id, Task.status == TaskStatus.OPEN)
        .order_by(Task.created_at.desc())
        .limit(args.limit)
    )
    tasks = (await db.execute(stmt)).scalars().all()
    return [
        {"id": t.id, "title": t.title, "priority": t.priority, "due_date": t.due_date}
        for t in tasks
    ]


LIST_OPEN_TASKS = ToolDefinition(
    name="list_open_tasks",
    description="List open (not yet completed) tasks for the organization.",
    args_schema=ListOpenTasksArgs,
    handler=_list_open_tasks,
)
