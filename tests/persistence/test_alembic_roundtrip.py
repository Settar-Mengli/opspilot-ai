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
                "oauth_credentials",
                "sync_cursors",
                "meetings",
                "mail_drafts",
                "mail_send_audit",
                "ops_jobs",
                "ops_job_lease",
                "triage_corrections",
                "anthropic_prepaid_budget",
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
                lease_row = conn.execute(
                    text("SELECT slot, job_id, generation FROM ops_job_lease WHERE slot = 1")
                ).one()
            assert version == "0010_ops_jobs_corrections_budget"
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
            work_cols = {c["name"] for c in inspect(engine).get_columns("work_items")}
            assert "provider_id" in work_cols
            assert "thread_id" in work_cols
            oauth_cols = {c["name"] for c in inspect(engine).get_columns("oauth_credentials")}
            assert "refresh_token_enc" in oauth_cols
            draft_cols = {c["name"] for c in inspect(engine).get_columns("mail_drafts")}
            assert "payload_sha256" in draft_cols
            assert "to_addrs" in draft_cols
            audit_cols = {c["name"] for c in inspect(engine).get_columns("mail_send_audit")}
            assert "idempotency_key" in audit_cols
            assert "demo_mode_blocked" in audit_cols
            assert lease_row.slot == 1
            assert lease_row.job_id is None
            assert lease_row.generation == 0
            ops_cols = {c["name"] for c in inspect(engine).get_columns("ops_jobs")}
            assert "metadata_json" in ops_cols
            assert "lease_generation" in ops_cols
        finally:
            engine.dispose()
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
