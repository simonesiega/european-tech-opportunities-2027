"""Minimal SQLAlchemy schema for searches, runs, jobs, and provenance."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from internships.database.base import Base


class SearchRow(Base):
    """Map a configured search to its database row."""

    __tablename__ = "searches"

    slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    keywords: Mapped[str] = mapped_column(String(300), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchRunRow(Base):
    """Map one search execution to its database row."""

    __tablename__ = "search_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    search_slug: Mapped[str] = mapped_column(
        ForeignKey("searches.slug", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    found_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(500))

    __table_args__ = (Index("ix_search_runs_latest", "search_slug", "finished_at"),)


class JobRow(Base):
    """Map a discovered job to its database row."""

    __tablename__ = "jobs"

    linkedin_job_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str] = mapped_column(String(500), nullable=False)
    link: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    industries: Mapped[str | None] = mapped_column(String(500))
    employment_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    start_date: Mapped[str | None] = mapped_column(String(100))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    __table_args__ = (
        CheckConstraint(
            "employment_type IN ('internship', 'new-grad')",
            name="ck_jobs_employment_type",
        ),
        Index("ix_jobs_readme", "status", "company", "title"),
    )


class JobSearchRow(Base):
    """Map job-to-search provenance to its database row."""

    __tablename__ = "job_searches"

    search_slug: Mapped[str] = mapped_column(
        ForeignKey("searches.slug", ondelete="CASCADE"), primary_key=True
    )
    linkedin_job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.linkedin_job_id", ondelete="CASCADE"), primary_key=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_run_id: Mapped[str] = mapped_column(
        ForeignKey("search_runs.id", ondelete="CASCADE"), nullable=False
    )
    unavailable_confirmations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
