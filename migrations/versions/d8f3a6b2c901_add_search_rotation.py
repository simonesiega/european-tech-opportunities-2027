"""Add per-search completion scheduling without changing lifecycle history."""

import sqlalchemy as sa
from alembic import op

revision = "d8f3a6b2c901"
down_revision = "b6e8d2f4a901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "searches", sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("searches", "last_completed_at")
