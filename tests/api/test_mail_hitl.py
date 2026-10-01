"""HITL mail draft edit + approve gates (D-033)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import app
from opspilot.api.deps import get_db_session, reset_db_engine
from opspilot.persistence.repositories import mail_drafts, work_items
from opspilot.services.operator_session import issue_session


@pytest.fixture()
def api_client(test_database_url: str, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-for-hitl-32b!!")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.delenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", raising=False)
    reset_db_engine()

    def _override() -> Iterator[Session]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db_session] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    reset_db_engine()


def _seed_draft(db_session: Session) -> str:
    wi = work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_hitl_1",
        source_type="gmail",
        subject_or_title="Hello",
        body_or_description="Body",
        sender_or_requester="demo@example.com",
        received_at=datetime(2026, 10, 1, tzinfo=UTC),
        thread_id="thr_hitl_1",
    )
    draft = mail_drafts.create_draft(
        db_session,
        work_item_id=wi,
        thread_id="thr_hitl_1",
        gmail_provider_id="msg_hitl_1",
        to_addrs="demo@example.com",
        subject="Re: Hello",
        body="Thanks",
        operator_email="ops@example.com",
    )
    db_session.commit()
    return draft.id


def _auth_cookie(client: TestClient) -> None:
    token = issue_session(email="ops@example.com")
    client.cookies.set("opspilot_operator", token)


def test_edit_rejects_to_addrs(api_client: TestClient, db_session: Session) -> None:
    draft_id = _seed_draft(db_session)
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/edit",
        json={"subject": "X", "body": "Y", "to_addrs": "evil@example.com"},
    )
    assert resp.status_code == 422


def test_edit_subject_body_ok(api_client: TestClient, db_session: Session) -> None:
    draft_id = _seed_draft(db_session)
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/edit",
        json={"subject": "Updated", "body": "New body"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["subject"] == "Updated"
    assert body["to_addrs"] == "demo@example.com"


def test_approve_demo_mode_403(api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "1")
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.com")
    draft_id = _seed_draft(db_session)
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/approve",
        json={"payload_sha256": draft.payload_sha256},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "demo_mode_blocks_send"


def test_approve_unset_allowlist_deny(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.delenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", raising=False)
    draft_id = _seed_draft(db_session)
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/approve",
        json={"payload_sha256": draft.payload_sha256},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "recipient_not_allowlisted"
