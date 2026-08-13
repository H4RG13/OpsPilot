import uuid

from sqlalchemy import CHAR
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    """Native UUID on PostgreSQL, CHAR(36) elsewhere (e.g. SQLite in tests)."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return str(value) if isinstance(value, uuid.UUID) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
