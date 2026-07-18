"""normalize opportunity employment types

Revision ID: f2b8d4c61a90
Revises: e4a7c9d21b60
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2b8d4c61a90"
down_revision: str | None = "e4a7c9d21b60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill existing listings as internships and require the normalized type."""
    # Every listing accepted before new-grad support was title-explicitly an internship.
    op.execute(sa.text("UPDATE jobs SET employment_type = 'internship'"))
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.alter_column(
            "employment_type",
            existing_type=sa.String(length=30),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_jobs_employment_type",
            "employment_type IN ('internship', 'new-grad')",
        )
        batch_op.create_index("ix_jobs_employment_type", ["employment_type"], unique=False)


def downgrade() -> None:
    """Restore the former optional, unindexed source-metadata field."""
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_index("ix_jobs_employment_type")
        batch_op.drop_constraint("ck_jobs_employment_type", type_="check")
        batch_op.alter_column(
            "employment_type",
            existing_type=sa.String(length=30),
            nullable=True,
        )
