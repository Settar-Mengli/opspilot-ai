"""Alembic round-trip against a dedicated throwaway database (A10)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect, text
from tests.db_support import alembic_downgrade, alembic_upgrade


@pytest.mark.alembic
def test_alembic_upgrade_downgrade_upgrade(alembic_throwaway_url: str) -> None:
    previous = os.environ.get("DATABASE_URL")
    try:
        alembic_upgrade(alembic_throwaway_url)
        engine = create_engine(alembic_throwaway_url)
        try:
            tables = set(inspect(engine).get_table_names())
            assert {
                "work_items",
                "runs",
                "run_artifacts",
                "triage_decisions",
                "alembic_version",
            }.issubset(tables)
        finally:
            engine.dispose()

        alembic_downgrade(alembic_throwaway_url)
        engine = create_engine(alembic_throwaway_url)
        try:
            tables = set(inspect(engine).get_table_names())
            assert "work_items" not in tables
            assert "runs" not in tables
        finally:
            engine.dispose()

        alembic_upgrade(alembic_throwaway_url)
        engine = create_engine(alembic_throwaway_url)
        try:
            with engine.connect() as conn:
                version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            assert version == "0001_initial"
        finally:
            engine.dispose()
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
