"""Engine + session factory for BoardWise, configured from `DATABASE_URL` (env
only — rule: config via env only; no secrets/URLs hardcoded in source).

Engines are built fresh per call (never cached at import time) so tests can
point at an isolated `tmp_path` SQLite file without needing to reload this
module between cases.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base

DEFAULT_DATABASE_URL = "sqlite:///./boardwise.sqlite3"


def get_database_url() -> str:
    """Return the configured `DATABASE_URL` (env var wins over the default)."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_engine(database_url: str | None = None) -> Engine:
    """Build a SQLAlchemy engine for `database_url` (defaults to the env URL)."""
    url = database_url or get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def get_sessionmaker(engine: Engine | None = None) -> sessionmaker[Session]:
    """Build a session factory bound to `engine` (defaults to `get_engine()`)."""
    return sessionmaker(
        bind=engine or get_engine(), autoflush=False, expire_on_commit=False
    )


@contextmanager
def session_scope(database_url: str | None = None) -> Iterator[Session]:
    """Yield a `Session` bound to `database_url` (or the env default).

    Ensures the schema exists (`Base.metadata.create_all`), commits on a clean
    exit, and rolls back on exception.
    """
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = get_sessionmaker(engine)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
