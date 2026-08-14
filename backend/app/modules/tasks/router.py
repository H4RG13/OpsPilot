import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, get_current_context, require_role
from app.modules.tasks import service
from app.modules.tasks.models import TaskPriority, TaskStatus
from app.modules.tasks.schemas import TaskCreate, TaskResponse, TaskUpdate
from app.shared.pagination import Page, PageParams
from app.shared.permissions import Role

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=Page[TaskResponse])
async def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    priority: TaskPriority | None = Query(default=None),
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> Page:
    params = PageParams(page=page, page_size=page_size)
    return await service.list_tasks(
        db, context.organization_id, params, status=status_filter, priority=priority
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await service.create_task(db, context.organization_id, context.user.id, data)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await service.get_task(db, context.organization_id, task_id)
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await service.update_task(db, context.organization_id, task_id, data)
    return TaskResponse.model_validate(task)
