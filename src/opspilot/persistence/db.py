"""Database engine and session helpers (sync SQLAlchemy + psycopg)."""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine as create_sa_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg://opspilot:opspilot@127.0.0.1:5432/opspilot"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL).strip() or DEFAULT_DATABASE_URL


def to_sync_url(url: str | None = None) -> str:
    """Return a sync SQLAlchemy URL (psycopg) for Alembic and sessions."""
    raw = url or get_database_url()
    parsed = make_url(raw)
    driver = parsed.drivername
    if "+psycopg" in driver or driver.endswith("+asyncpg"):
        parsed = parsed.set(drivername="postgresql+psycopg")
    elif driver == "postgresql":
        parsed = parsed.set(drivername="postgresql+psycopg")
    return parsed.render_as_string(hide_password=False)


def create_engine(url: str | None = None, *, echo: bool = False) -> Engine:
    return create_sa_engine(to_sync_url(url), echo=echo, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False, class_=Session)


# Aliases used by deps.py during the sync unification.
create_sync_engine = create_engine
create_sync_session_factory = create_session_factory


def sync_session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        yield session
