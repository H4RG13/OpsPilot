import json
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.audit.models import AuditLog


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    metadata: dict | None
    created_at: datetime


def audit_log_to_response(entry: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=entry.id,
        user_id=entry.user_id,
        action=entry.action,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        metadata=json.loads(entry.event_metadata) if entry.event_metadata else None,
        created_at=entry.created_at,
    )
