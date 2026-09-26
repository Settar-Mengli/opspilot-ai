"""FastAPI dependencies (sync sessions — Windows uvicorn/Proactor safe)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from opspilot.persistence.db import create_sync_engine, create_sync_session_factory, get_database_url

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _get_factory() -> sessionmaker[Session]:
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_sync_engine(get_database_url())
        _session_factory = create_sync_session_factory(_engine)
    return _session_factory


def get_db_session() -> Iterator[Session]:
    factory = _get_factory()
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def reset_db_engine() -> None:
    """Test helper: drop cached engine so DATABASE_URL changes take effect."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
