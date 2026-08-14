import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID


class ImportType(StrEnum):
    CUSTOMERS = "customers"
    PRODUCTS = "products"


class ImportStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    import_type: Mapped[ImportType] = mapped_column(
        SqlEnum(ImportType, native_enum=False, length=20), nullable=False
    )
    status: Mapped[ImportStatus] = mapped_column(
        SqlEnum(ImportStatus, native_enum=False, length=20),
        nullable=False,
        default=ImportStatus.QUEUED,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Raw CSV text stored inline rather than in object storage — the spec
    # calls out object storage explicitly as an "optional later" item
    # (Section 4), and files here are small demo-scale CSVs.
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    total_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imported_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failed_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
