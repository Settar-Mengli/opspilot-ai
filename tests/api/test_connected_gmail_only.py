"""G7: when Google is connected, operator surfaces use gmail-only (sample hidden)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import create_app
from opspilot.api.deps import reset_db_engine
from opspilot.persistence.models import RunArtifactRow, RunRow, TriageDecisionRow
from opspilot.persistence.repositories import oauth_credentials, work_items
from opspilot.services.operator_session import issue_session


@pytest.fixture
def g7_client(monkeypatch: pytest.MonkeyPatch, test_database_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-not-real")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    reset_db_engine()
    return TestClient(create_app())


def _seed_mixed_queue(db_session: Session) -> None:
    t0 = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
    sample_id = work_items.upsert_by_provider_id(
        db_session,
        provider_id="sample-1",
        source_type="email",
        subject_or_title="SAMPLE Checkout errors",
        body_or_description="sample body",
        sender_or_requester="sample@example.com",
        received_at=t0,
    )
    gmail_id = work_items.upsert_by_provider_id(
        db_session,
        provider_id="gmail-1",
        source_type="gmail",
        subject_or_title="Real inbox subject",
        body_or_description="gmail body",
        sender_or_requester="real@example.com",
        received_at=t0.replace(hour=14),
    )
    db_session.add(
        RunRow(
            run_id="run-sample-001",
            started_at=t0,
            finished_at=t0,
            status="success",
            metadata_json={"run_id": "run-sample-001", "input_file": "sample_input.json"},
        )
    )
    db_session.add(
        RunRow(
            run_id="run-gmail-001",
            started_at=t0.replace(hour=15),
            finished_at=t0.replace(hour=15),
            status="success",
            metadata_json={"run_id": "run-gmail-001", "input_file": "db:gmail"},
        )
    )
    db_session.add(
        TriageDecisionRow(
            work_item_id=sample_id,
            run_id="run-sample-001",
            urgency="high",
            urgency_reason="sample",
            category="incident",
            category_reason="sample",
            sentiment="negative",
            sentiment_reason="sample",
        )
    )
    db_session.add(
        TriageDecisionRow(
            work_item_id=gmail_id,
            run_id="run-gmail-001",
            urgency="medium",
            urgency_reason="gmail",
            category="request",
            category_reason="gmail",
            sentiment="neutral",
            sentiment_reason="gmail",
        )
    )
    db_session.add(
        RunArtifactRow(
            run_id="run-sample-001",
            name="daily_briefing",
            content_type="text",
            content="SAMPLE BRIEFING ONLY",
        )
    )
    db_session.add(
        RunArtifactRow(
            run_id="run-gmail-001",
            name="daily_briefing",
            content_type="text",
            content="GMAIL BRIEFING ONLY",
        )
    )
    db_session.add(
        RunArtifactRow(
            run_id="run-gmail-001",
            name="ai_briefing",
            content_type="text",
            content="GMAIL AI BRIEFING",
        )
    )
    db_session.commit()


def _connect_google(db_session: Session) -> None:
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes=(
            "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar.readonly"
        ),
        refresh_token_plaintext="rt",
    )
    db_session.commit()


def test_disconnected_triage_includes_sample(g7_client: TestClient, db_session: Session) -> None:
    _seed_mixed_queue(db_session)
    resp = g7_client.get("/api/v1/triage")
    assert resp.status_code == 200
    titles = {r["subject_or_title"] for r in resp.json()}
    assert "SAMPLE Checkout errors" in titles
    assert "Real inbox subject" in titles


def test_connected_triage_excludes_sample(g7_client: TestClient, db_session: Session) -> None:
    _seed_mixed_queue(db_session)
    _connect_google(db_session)
    resp = g7_client.get("/api/v1/triage")
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 1
    assert payload[0]["subject_or_title"] == "Real inbox subject"


def test_connected_briefing_uses_gmail_run(g7_client: TestClient, db_session: Session) -> None:
    _seed_mixed_queue(db_session)
    _connect_google(db_session)
    assert g7_client.get("/api/v1/briefing").text == "GMAIL BRIEFING ONLY"
    assert g7_client.get("/api/v1/ai-briefing").text == "GMAIL AI BRIEFING"


def test_disconnected_briefing_can_be_sample(g7_client: TestClient, db_session: Session) -> None:
    _seed_mixed_queue(db_session)
    # Newest artifact id wins when disconnected — gmail run was inserted later, so either is ok
    # as long as we don't 404. Prefer asserting sample still reachable via run-scoped route.
    resp = g7_client.get("/api/v1/runs/run-sample-001/briefing")
    assert resp.status_code == 200
    assert resp.text == "SAMPLE BRIEFING ONLY"


def test_connected_ask_context_omits_sample(
    g7_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_mixed_queue(db_session)
    _connect_google(db_session)
    captured: dict[str, object] = {}

    def _capture(*, question: str, triage_records=None, **kwargs):  # noqa: ANN001
        captured["records"] = list(triage_records or [])
        return "ok"

    monkeypatch.setattr("opspilot.api.v1.routes.answer_question", _capture)
    token = issue_session(email="demo@example.com")
    g7_client.cookies.set("opspilot_operator", token)
    resp = g7_client.post("/api/v1/ask", json={"question": "What is urgent?"})
    assert resp.status_code == 200
    records = captured["records"]
    assert isinstance(records, list)
    assert len(records) == 1
    assert records[0]["subject_or_title"] == "Real inbox subject"  # type: ignore[index]
