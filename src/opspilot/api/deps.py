"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from opspilot.persistence.db import create_engine, create_session_factory, get_database_url

_engine = None
_session_factory = None


def _get_factory():
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_engine(get_database_url())
        _session_factory = create_session_factory(_engine)
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    factory = _get_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def reset_db_engine() -> None:
    """Test helper: drop cached engine so DATABASE_URL changes take effect."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
