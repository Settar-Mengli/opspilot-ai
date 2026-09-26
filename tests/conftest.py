"""Shared pytest fixtures for hermetic, order-independent tests."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine as create_admin_engine
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from tests.db_support import alembic_upgrade as _alembic_upgrade

from opspilot.persistence.db import create_engine, create_session_factory, to_sync_url

TEST_DB_NAME = "opspilot_test"
ALEMBIC_RT_DB_NAME = "opspilot_alembic_rt"
DEFAULT_ADMIN_URL = "postgresql+psycopg://opspilot:opspilot@127.0.0.1:5432/postgres"


@pytest.fixture(autouse=True)
def _force_rules_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force rule-based triage for every test; subprocesses inherit this env."""
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")


@pytest.fixture(autouse=True)
def _block_real_anthropic_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the suite if anthropic.Anthropic is constructed during a test."""
    import anthropic

    def _forbidden(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(
            "anthropic.Anthropic must not be constructed during tests (OPSPILOT_FORCE_RULES / hermetic guard)"
        )

    monkeypatch.setattr(anthropic, "Anthropic", _forbidden)


def _base_url_from_env() -> str:
    raw = os.environ.get("DATABASE_URL", "").strip()
    if raw:
        return to_sync_url(raw)
    return DEFAULT_ADMIN_URL.replace("/postgres", "/opspilot")


def _admin_sync_url() -> str:
    parsed = make_url(_base_url_from_env())
    return parsed.set(database="postgres").render_as_string(hide_password=False)


def _db_url(database: str) -> str:
    parsed = make_url(_base_url_from_env())
    return parsed.set(drivername="postgresql+psycopg", database=database).render_as_string(hide_password=False)


def _ensure_database(database: str) -> None:
    engine = create_admin_engine(_admin_sync_url(), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{database}"'))
    finally:
        engine.dispose()


def _drop_database(database: str) -> None:
    engine = create_admin_engine(_admin_sync_url(), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": database},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{database}"'))
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> Iterator[str]:
    """Truncate-managed test DB URL (created once per session)."""
    _ensure_database(TEST_DB_NAME)
    url = _db_url(TEST_DB_NAME)
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    _alembic_upgrade(url)
    try:
        yield url
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


@pytest.fixture
def db_session(test_database_url: str) -> Iterator[Session]:
    """Per-test session against truncate-managed opspilot_test."""
    engine = create_engine(test_database_url)
    factory = create_session_factory(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE triage_decisions, run_artifacts, runs, work_items RESTART IDENTITY CASCADE"))
    with factory() as session:
        yield session
        session.rollback()
    engine.dispose()


@pytest.fixture
def alembic_throwaway_url() -> Iterator[str]:
    """Dedicated DB for Alembic round-trip; created and dropped by this fixture."""
    _drop_database(ALEMBIC_RT_DB_NAME)
    _ensure_database(ALEMBIC_RT_DB_NAME)
    url = _db_url(ALEMBIC_RT_DB_NAME)
    try:
        yield url
    finally:
        _drop_database(ALEMBIC_RT_DB_NAME)
