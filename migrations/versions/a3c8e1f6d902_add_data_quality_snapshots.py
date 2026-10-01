"""add aggregate data-quality snapshots

Revision ID: a3c8e1f6d902
Revises: a9c4e72b5d18
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3c8e1f6d902"
down_revision: str | None = "a9c4e72b5d18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create bounded storage for aggregate-only monitoring baselines."""
    op.create_table(
        "data_quality_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_quality_snapshots_captured_at",
        "data_quality_snapshots",
        ["captured_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove aggregate data-quality baselines."""
    op.drop_index(
        "ix_data_quality_snapshots_captured_at",
        table_name="data_quality_snapshots",
    )
    op.drop_table("data_quality_snapshots")
