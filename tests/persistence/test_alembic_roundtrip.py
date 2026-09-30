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
                "llm_calls",
                "llm_budget_counters",
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
            assert "llm_calls" not in tables
        finally:
            engine.dispose()

        alembic_upgrade(alembic_throwaway_url)
        engine = create_engine(alembic_throwaway_url)
        try:
            with engine.connect() as conn:
                version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            assert version == "0006_triage_confidence_evidence"
            indexes = {idx["name"] for idx in inspect(engine).get_indexes("runs")}
            assert "ix_runs_finished_at" in indexes
            llm_indexes = {idx["name"] for idx in inspect(engine).get_indexes("llm_calls")}
            assert "ix_llm_calls_created_at" in llm_indexes
            artifact_indexes = {idx["name"] for idx in inspect(engine).get_indexes("run_artifacts")}
            assert "ix_run_artifacts_name" in artifact_indexes
            cols = {c["name"]: c for c in inspect(engine).get_columns("runs")}
            assert (
                "DateTime" in str(cols["finished_at"]["type"])
                or "TIMESTAMP" in str(cols["finished_at"]["type"]).upper()
            )
            triage_cols = {c["name"] for c in inspect(engine).get_columns("triage_decisions")}
            assert "confidence" in triage_cols
            assert "evidence_refs" in triage_cols
        finally:
            engine.dispose()
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
