"""Tests for POST/DELETE /api/v1/corrections/{work_item_id} (B6 C6)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.persistence.models import (
    RunRow,
    TriageDecisionRow,
    WorkItemRow,
)
from opspilot.services.operator_session import issue_session

COOKIE_NAME = "opspilot_operator"


@pytest.fixture()
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-secret-corrections")
    monkeypatch.setenv("OPSPILOT_CSRF_RELAX_DEV", "1")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")


@pytest.fixture()
def client(_env: None) -> TestClient:
    from opspilot.api.app import create_app

    return TestClient(create_app())


@pytest.fixture()
def operator_cookie(_env: None) -> dict[str, str]:
    token = issue_session(email="ops@example.com")
    return {COOKIE_NAME: token}


def _seed(session: Session) -> str:
    wid = "wi_corr_test_1"
    session.add(
        WorkItemRow(
            id=wid,
            source_type="gmail",
            subject_or_title="Correction test",
            body_or_description="Body",
            sender_or_requester="user@example.com",
            received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
            tags=[],
        )
    )
    session.add(RunRow(run_id="run_corr", status="success"))
    session.add(
        TriageDecisionRow(
            work_item_id=wid,
            run_id="run_corr",
            urgency="low",
            urgency_reason="auto",
            category="info",
            category_reason="auto",
            sentiment="neutral",
            sentiment_reason="auto",
        )
    )
    session.commit()
    return wid


def test_post_correction_upserts(client: TestClient, operator_cookie: dict[str, str], db_session: Session) -> None:
    wid = _seed(db_session)
    resp = client.post(
        f"/api/v1/corrections/{wid}",
        json={"urgency": "high", "category": "action", "sentiment": "negative"},
        cookies=operator_cookie,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["corrected"] is True
    assert data["urgency"] == "high"


def test_delete_correction(client: TestClient, operator_cookie: dict[str, str], db_session: Session) -> None:
    wid = _seed(db_session)
    client.post(
        f"/api/v1/corrections/{wid}",
        json={"urgency": "high", "category": "action", "sentiment": "negative"},
        cookies=operator_cookie,
    )
    resp = client.delete(f"/api/v1/corrections/{wid}", cookies=operator_cookie)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


def test_delete_nonexistent_404(client: TestClient, operator_cookie: dict[str, str], db_session: Session) -> None:
    _seed(db_session)
    resp = client.delete("/api/v1/corrections/nonexistent", cookies=operator_cookie)
    assert resp.status_code == 404


def test_post_correction_work_item_not_found(
    client: TestClient, operator_cookie: dict[str, str], db_session: Session
) -> None:
    _seed(db_session)
    resp = client.post(
        "/api/v1/corrections/nonexistent",
        json={"urgency": "high", "category": "action", "sentiment": "negative"},
        cookies=operator_cookie,
    )
    assert resp.status_code == 404


def test_post_correction_no_auth(client: TestClient, db_session: Session) -> None:
    wid = _seed(db_session)
    resp = client.post(
        f"/api/v1/corrections/{wid}",
        json={"urgency": "high", "category": "action", "sentiment": "negative"},
    )
    assert resp.status_code == 401


def test_demo_mode_blocks_correction(
    client: TestClient, operator_cookie: dict[str, str], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    wid = _seed(db_session)
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "1")
    resp = client.post(
        f"/api/v1/corrections/{wid}",
        json={"urgency": "high", "category": "action", "sentiment": "negative"},
        cookies=operator_cookie,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "demo_mode"


def test_demo_mode_blocks_delete(
    client: TestClient, operator_cookie: dict[str, str], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "1")
    resp = client.delete("/api/v1/corrections/any_id", cookies=operator_cookie)
    assert resp.status_code == 403


def test_triage_endpoint_shows_corrected_field(
    client: TestClient, operator_cookie: dict[str, str], db_session: Session
) -> None:
    """GET /triage returns corrected: bool in each record after overlay."""
    wid = _seed(db_session)
    client.post(
        f"/api/v1/corrections/{wid}",
        json={"urgency": "critical", "category": "escalation", "sentiment": "negative"},
        cookies=operator_cookie,
    )
    resp = client.get("/api/v1/triage")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    item = next(i for i in items if i["id"] == wid)
    assert item["corrected"] is True
    assert item["urgency"] == "critical"
    assert item["urgency_reason"] == "auto"
