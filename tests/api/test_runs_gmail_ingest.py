"""POST /runs uses DB gmail ingest when Google is connected."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from opspilot.api.app import create_app
from opspilot.api.deps import reset_db_engine
from opspilot.persistence.models import TriageDecisionRow, WorkItemRow
from opspilot.persistence.repositories import oauth_credentials, work_items


@pytest.fixture
def runs_client(monkeypatch: pytest.MonkeyPatch, test_database_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-not-real")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    reset_db_engine()
    return TestClient(create_app())


def _seed_gmail(db_session: Session, *, provider_id: str, title: str) -> str:
    return work_items.upsert_by_provider_id(
        db_session,
        provider_id=provider_id,
        source_type="gmail",
        subject_or_title=title,
        body_or_description="body",
        sender_or_requester="sender@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
    )


def test_run_connected_triages_gmail_provider_ids(runs_client: TestClient, db_session: Session) -> None:
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes=(
            "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar.readonly"
        ),
        refresh_token_plaintext="rt-fixture",
    )
    pid1 = "gmail_msg_aaa"
    pid2 = "gmail_msg_bbb"
    _seed_gmail(db_session, provider_id=pid1, title="Northwind invoice")
    _seed_gmail(db_session, provider_id=pid2, title="Helix follow-up")
    db_session.commit()

    resp = runs_client.post("/api/v1/runs", json={"date": date.today().isoformat()})
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["run_id"]

    decisions = db_session.scalars(select(TriageDecisionRow).where(TriageDecisionRow.run_id == run_id)).all()
    assert len(decisions) == 2
    wi_ids = {d.work_item_id for d in decisions}
    rows = db_session.scalars(select(WorkItemRow).where(WorkItemRow.id.in_(wi_ids))).all()
    provider_ids = {r.provider_id for r in rows}
    assert provider_ids == {pid1, pid2}
    assert all(r.source_type == "gmail" for r in rows)


def test_run_disconnected_uses_sample(runs_client: TestClient, db_session: Session) -> None:
    assert oauth_credentials.is_connected(db_session, provider="google") is False
    resp = runs_client.post("/api/v1/runs", json={"date": date.today().isoformat()})
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["run_id"]
    decisions = db_session.scalars(select(TriageDecisionRow).where(TriageDecisionRow.run_id == run_id)).all()
    assert len(decisions) == 13
    wi_ids = {d.work_item_id for d in decisions}
    rows = db_session.scalars(select(WorkItemRow).where(WorkItemRow.id.in_(wi_ids))).all()
    assert all(r.provider_id is None for r in rows)
    assert all(r.source_type != "gmail" for r in rows)
