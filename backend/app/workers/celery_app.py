from celery import Celery

from app.core.config import settings

# Import every ORM model so Base.metadata is fully populated before any task
# runs. The FastAPI app gets this for free by importing all routers at
# startup; this worker process only imports the task modules above, so
# without this, a task that flushes a model with a cross-module FK (e.g.
# ImportJob.created_by -> users.id) fails with NoReferencedTableError because
# the referenced table's model was never imported. Mirrors migrations/env.py.
from app.modules.ai.models import AIConversation, AIMessage, AIUsage  # noqa: F401
from app.modules.audit.models import AuditLog  # noqa: F401
from app.modules.auth.models import RefreshToken  # noqa: F401
from app.modules.customers.models import Customer  # noqa: F401
from app.modules.imports.models import ImportJob  # noqa: F401
from app.modules.orders.models import Order, OrderItem  # noqa: F401
from app.modules.organizations.models import Organization, OrganizationMember  # noqa: F401
from app.modules.products.models import Product  # noqa: F401
from app.modules.reports.models import Report  # noqa: F401
from app.modules.tasks.models import Task  # noqa: F401
from app.modules.users.models import User  # noqa: F401

celery_app = Celery(
    settings.app_name,
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks", "app.modules.reports.tasks", "app.modules.imports.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
