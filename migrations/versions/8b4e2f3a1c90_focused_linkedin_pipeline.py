"""focused LinkedIn to SQLite to README schema

Revision ID: 8b4e2f3a1c90
Revises:
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8b4e2f3a1c90"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the focused LinkedIn pipeline schema."""
    op.create_table(
        "searches",
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("keywords", sa.String(length=300), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("config_hash", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("slug"),
    )
    op.create_table(
        "jobs",
        sa.Column("linkedin_job_id", sa.String(length=30), nullable=False),
        sa.Column("company", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=False),
        sa.Column("link", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("linkedin_job_id"),
        sa.UniqueConstraint("link"),
    )
    op.create_index("ix_jobs_category", "jobs", ["category"])
    op.create_index("ix_jobs_company", "jobs", ["company"])
    op.create_index("ix_jobs_readme", "jobs", ["status", "company", "title"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_table(
        "search_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("search_slug", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("found_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("excluded_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["search_slug"], ["searches.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_runs_latest", "search_runs", ["search_slug", "finished_at"])
    op.create_index("ix_search_runs_search_slug", "search_runs", ["search_slug"])
    op.create_index("ix_search_runs_status", "search_runs", ["status"])
    op.create_table(
        "job_searches",
        sa.Column("search_slug", sa.String(length=100), nullable=False),
        sa.Column("linkedin_job_id", sa.String(length=30), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_run_id", sa.String(length=36), nullable=False),
        sa.Column("unavailable_confirmations", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["linkedin_job_id"], ["jobs.linkedin_job_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_seen_run_id"], ["search_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["search_slug"], ["searches.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("search_slug", "linkedin_job_id"),
    )
    op.create_index("ix_job_searches_active", "job_searches", ["active"])


def downgrade() -> None:
    """Remove the focused LinkedIn pipeline schema."""
    op.drop_index("ix_job_searches_active", table_name="job_searches")
    op.drop_table("job_searches")
    op.drop_index("ix_search_runs_status", table_name="search_runs")
    op.drop_index("ix_search_runs_search_slug", table_name="search_runs")
    op.drop_index("ix_search_runs_latest", table_name="search_runs")
    op.drop_table("search_runs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_readme", table_name="jobs")
    op.drop_index("ix_jobs_company", table_name="jobs")
    op.drop_index("ix_jobs_category", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("searches")
