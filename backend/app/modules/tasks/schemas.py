import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.tasks.models import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to: uuid.UUID | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    assigned_to: uuid.UUID | None = None
    due_date: date | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    created_by: uuid.UUID | None
    assigned_to: uuid.UUID | None
    title: str
    description: str | None
    priority: TaskPriority
    status: TaskStatus
    due_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}
