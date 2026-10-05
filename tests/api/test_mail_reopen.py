"""POST /api/v1/mail/drafts/{id}/reopen (B6 C7)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import app
from opspilot.api.deps import get_db_session, reset_db_engine
from opspilot.persistence.repositories import mail_drafts, mail_send_audit, work_items
from opspilot.services.operator_session import issue_session


@pytest.fixture()
def api_client(test_database_url: str, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-for-reopen-32!")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_CSRF_RELAX_DEV", "1")
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


def _seed_draft(
    db_session: Session,
    *,
    status: str = "draft",
    operator_email: str = "ops@example.com",
    provider_id: str = "msg_reopen_1",
) -> str:
    wi = work_items.upsert_by_provider_id(
        db_session,
        provider_id=provider_id,
        source_type="gmail",
        subject_or_title="Hello",
        body_or_description="Body",
        sender_or_requester="demo@example.com",
        received_at=datetime(2026, 10, 1, tzinfo=UTC),
        thread_id="thr_reopen_1",
    )
    draft = mail_drafts.create_draft(
        db_session,
        work_item_id=wi,
        thread_id="thr_reopen_1",
        gmail_provider_id=provider_id,
        to_addrs="demo@example.com",
        subject="Re: Hello",
        body="Thanks",
        operator_email=operator_email,
    )
    if status != "draft":
        mail_drafts.set_status(db_session, draft, status)
    db_session.commit()
    return draft.id


def _auth(client: TestClient, email: str = "ops@example.com") -> None:
    client.cookies.set("opspilot_operator", issue_session(email=email))


def _audit_failed(
    db_session: Session,
    draft_id: str,
    *,
    error_code: str,
    payload_sha256: str,
) -> None:
    mail_send_audit.insert_audit(
        db_session,
        draft_id=draft_id,
        idempotency_key=f"idem-{error_code}-{draft_id}",
        to_addrs="demo@example.com",
        payload_sha256=payload_sha256,
        operator_email="ops@example.com",
        send_failed=True,
        error_code=error_code,
    )
    db_session.commit()


@pytest.mark.parametrize(
    ("status", "error_code", "expected_status", "expected_code"),
    [
        ("draft", None, 409, "draft_not_failed"),
        ("approved", None, 409, "draft_not_failed"),
        ("sent", None, 409, "already_sent"),
        ("cancelled", None, 409, "draft_not_failed"),
        ("failed", "no_google_credential", 200, None),
        ("failed", "google_reauth_required", 200, None),
        ("failed", "gmail_send_failed", 200, None),
        ("failed", "upstream_429", 200, None),
        ("draft", "send_outcome_unknown", 409, "draft_not_failed"),
        ("draft", "gmail_unavailable_not_sent", 409, "draft_not_failed"),
    ],
    ids=[
        "draft",
        "approved",
        "sent",
        "cancelled",
        "failed_no_cred",
        "failed_reauth",
        "failed_gmail",
        "failed_upstream",
        "draft_outcome_unknown",
        "draft_unavailable",
    ],
)
def test_reopen_matrix(
    api_client: TestClient,
    db_session: Session,
    status: str,
    error_code: str | None,
    expected_status: int,
    expected_code: str | None,
) -> None:
    draft_id = _seed_draft(db_session, status=status, provider_id=f"msg_mx_{status}_{error_code or 'none'}")
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    if error_code is not None:
        _audit_failed(db_session, draft_id, error_code=error_code, payload_sha256=draft.payload_sha256)
        if status == "failed" and error_code in {"send_outcome_unknown", "gmail_unavailable_not_sent"}:
            mail_drafts.set_status(db_session, draft, "draft")
            db_session.commit()

    _auth(api_client)
    resp = api_client.post(f"/api/v1/mail/drafts/{draft_id}/reopen")
    assert resp.status_code == expected_status
    if expected_code is not None:
        assert resp.json()["error"]["code"] == expected_code
    else:
        body = resp.json()
        assert body["status"] == "draft"
        assert body["id"] == draft_id
        refreshed = mail_drafts.get_draft(db_session, draft_id)
        assert refreshed is not None
        assert refreshed.status == "draft"


def test_reopen_demo_mode_403(api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "1")
    draft_id = _seed_draft(db_session, status="failed", provider_id="msg_reopen_demo")
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    _audit_failed(db_session, draft_id, error_code="no_google_credential", payload_sha256=draft.payload_sha256)
    _auth(api_client)
    resp = api_client.post(f"/api/v1/mail/drafts/{draft_id}/reopen")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "demo_mode"


def test_reopen_owner_mismatch_403(api_client: TestClient, db_session: Session) -> None:
    draft_id = _seed_draft(db_session, status="failed", provider_id="msg_reopen_owner")
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    _audit_failed(db_session, draft_id, error_code="gmail_send_failed", payload_sha256=draft.payload_sha256)
    _auth(api_client, email="other@example.com")
    resp = api_client.post(f"/api/v1/mail/drafts/{draft_id}/reopen")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "draft_owner_mismatch"


def test_reopen_not_found_404(api_client: TestClient) -> None:
    _auth(api_client)
    resp = api_client.post("/api/v1/mail/drafts/md_missing/reopen")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "draft_not_found"
