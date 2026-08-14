"""import_jobs

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("import_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=True),
        sa.Column("imported_rows", sa.Integer(), nullable=True),
        sa.Column("failed_rows", sa.Integer(), nullable=True),
        sa.Column("errors", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_import_jobs_organization_id", "import_jobs", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_import_jobs_organization_id", table_name="import_jobs")
    op.drop_table("import_jobs")
