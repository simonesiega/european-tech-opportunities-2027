"""Database engine and transaction factories."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

EXPECTED_TABLES = frozenset({"alembic_version", "searches", "search_runs", "jobs", "job_searches"})


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create an engine and enable SQLite integrity safeguards."""
    url = make_url(database_url)
    database_path = url.database
    if (
        url.get_backend_name() == "sqlite"
        and database_path is not None
        and database_path not in {"", ":memory:"}
    ):
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    connect_args = (
        {"check_same_thread": False, "timeout": 30} if url.get_backend_name() == "sqlite" else {}
    )
    engine = create_engine(database_url, echo=echo, future=True, connect_args=connect_args)
    if url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: object, _connection_record: object) -> None:
            """Enable SQLite foreign-key enforcement."""
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def database_exists(database_url: str) -> bool:
    """Return whether a file-backed SQLite database already exists."""
    url = make_url(database_url)
    database_path = url.database
    if url.get_backend_name() != "sqlite" or database_path is None:
        return True
    if database_path in {"", ":memory:"}:
        return True
    return Path(database_path).is_file()


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the database session factory."""
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False, autoflush=False)


def missing_tables(engine: Engine) -> set[str]:
    """Return required tables absent from the database."""
    return set(EXPECTED_TABLES) - set(inspect(engine).get_table_names())


def database_revision(engine: Engine) -> str | None:
    """Return the database migration revision when available."""
    if "alembic_version" not in inspect(engine).get_table_names():
        return None
    with engine.connect() as connection:
        value = connection.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
    return str(value) if value is not None else None
