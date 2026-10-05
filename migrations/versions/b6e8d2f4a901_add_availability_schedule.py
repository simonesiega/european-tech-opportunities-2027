"""add bounded availability audit scheduling

Revision ID: b6e8d2f4a901
Revises: a3c8e1f6d902
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b6e8d2f4a901"
down_revision: str | None = "a3c8e1f6d902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Preserve existing rows as never audited; selection limits the initial backlog."""
    op.add_column(
        "jobs",
        sa.Column("last_availability_checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_jobs_availability", "jobs", ["last_availability_checked_at", "first_seen_at"]
    )


def downgrade() -> None:
    """Remove scheduling metadata without removing listings or provenance."""
    op.drop_index("ix_jobs_availability", table_name="jobs")
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("last_availability_checked_at")
