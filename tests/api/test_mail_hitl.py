"""HITL mail draft edit + approve gates (D-033)."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from datetime import UTC, datetime
from email import message_from_bytes

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import app
from opspilot.api.deps import get_db_session, reset_db_engine
from opspilot.persistence.repositories import mail_drafts, mail_send_audit, oauth_credentials, work_items
from opspilot.services import mail_hitl
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


def _seed_draft(
    db_session: Session,
    *,
    operator_email: str = "ops@example.com",
    to_addrs: str = "demo@example.com",
    provider_id: str = "msg_hitl_1",
    thread_id: str = "thr_hitl_1",
) -> str:
    wi = work_items.upsert_by_provider_id(
        db_session,
        provider_id=provider_id,
        source_type="gmail",
        subject_or_title="Hello",
        body_or_description="Body",
        sender_or_requester=to_addrs,
        received_at=datetime(2026, 10, 1, tzinfo=UTC),
        thread_id=thread_id,
    )
    draft = mail_drafts.create_draft(
        db_session,
        work_item_id=wi,
        thread_id=thread_id,
        gmail_provider_id=provider_id,
        to_addrs=to_addrs,
        subject="Re: Hello",
        body="Thanks",
        operator_email=operator_email,
    )
    db_session.commit()
    return draft.id


def _auth_cookie(client: TestClient, email: str = "ops@example.com") -> None:
    token = issue_session(email=email)
    client.cookies.set("opspilot_operator", token)


def test_edit_rejects_to_addrs(api_client: TestClient, db_session: Session) -> None:
    draft_id = _seed_draft(db_session)
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/edit",
        json={"subject": "X", "body": "Y", "to_addrs": "evil@example.com"},
    )
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "field",
    ["thread_id", "gmail_provider_id", "work_item_id", "id", "status", "payload_sha256"],
)
def test_edit_rejects_forbidden_field(api_client: TestClient, db_session: Session, field: str) -> None:
    draft_id = _seed_draft(db_session, provider_id=f"msg_forbid_{field}")
    _auth_cookie(api_client)
    payload = {"subject": "X", "body": "Y", field: "smuggled"}
    resp = api_client.post(f"/api/v1/mail/drafts/{draft_id}/edit", json=payload)
    assert resp.status_code == 422


def test_edit_rejects_subject_newline_bcc_smuggle(api_client: TestClient, db_session: Session) -> None:
    draft_id = _seed_draft(db_session, provider_id="msg_subj_nl")
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/edit",
        json={"subject": "Hello\nBcc: evil@x.com", "body": "Y"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "unsafe_subject"


def test_edit_subject_body_ok(api_client: TestClient, db_session: Session) -> None:
    draft_id = _seed_draft(db_session, provider_id="msg_edit_ok")
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/edit",
        json={"subject": "Updated", "body": "New body"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["subject"] == "Updated"
    assert body["to_addrs"] == "demo@example.com"


def test_edit_non_draft_status_409(api_client: TestClient, db_session: Session) -> None:
    draft_id = _seed_draft(db_session, provider_id="msg_edit_sent")
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    mail_drafts.set_status(db_session, draft, "sent")
    db_session.commit()
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/edit",
        json={"subject": "X", "body": "Y"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "draft_not_editable"


def test_edit_owner_mismatch_403(api_client: TestClient, db_session: Session) -> None:
    draft_id = _seed_draft(db_session, operator_email="owner@example.com", provider_id="msg_own_edit")
    _auth_cookie(api_client, email="other@example.com")
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/edit",
        json={"subject": "X", "body": "Y"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "draft_owner_mismatch"


def test_approve_demo_mode_403(api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "1")
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.com")
    draft_id = _seed_draft(db_session, provider_id="msg_demo")
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
    draft_id = _seed_draft(db_session, provider_id="msg_allow")
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/approve",
        json={"payload_sha256": draft.payload_sha256},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "recipient_not_allowlisted"


def test_approve_cancelled_failed_sent_409(api_client: TestClient, db_session: Session) -> None:
    for status in ("cancelled", "failed", "sent"):
        draft_id = _seed_draft(db_session, provider_id=f"msg_{status}", to_addrs=f"{status}@example.com")
        draft = mail_drafts.get_draft(db_session, draft_id)
        assert draft is not None
        mail_drafts.set_status(db_session, draft, status)
        db_session.commit()
        _auth_cookie(api_client)
        resp = api_client.post(
            f"/api/v1/mail/drafts/{draft_id}/approve",
            json={"payload_sha256": draft.payload_sha256},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "draft_not_approvable"


def test_approve_payload_hash_mismatch(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.com")
    draft_id = _seed_draft(db_session, provider_id="msg_hash")
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/approve",
        json={"payload_sha256": "0" * 64},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "payload_hash_mismatch"


def test_approve_owner_mismatch_403(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.com")
    draft_id = _seed_draft(db_session, operator_email="owner@example.com", provider_id="msg_own_appr")
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    _auth_cookie(api_client, email="intruder@example.com")
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/approve",
        json={"payload_sha256": draft.payload_sha256},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "draft_owner_mismatch"


def test_approve_daily_cap_429(api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.com")
    monkeypatch.setenv("OPSPILOT_SEND_MAX_PER_DAY", "1")
    prior = _seed_draft(db_session, provider_id="msg_cap_prior")
    draft_row = mail_drafts.get_draft(db_session, prior)
    assert draft_row is not None
    mail_send_audit.insert_audit(
        db_session,
        draft_id=prior,
        idempotency_key="prior-success",
        to_addrs=draft_row.to_addrs,
        payload_sha256=draft_row.payload_sha256,
        gmail_message_id="gmail_prior",
        operator_email="ops@example.com",
    )
    db_session.commit()

    draft_b = mail_drafts.create_draft(
        db_session,
        work_item_id=None,
        thread_id="thr_cap",
        gmail_provider_id="msg_cap",
        to_addrs="demo@example.com",
        subject="Cap",
        body="Body",
        operator_email="ops@example.com",
    )
    db_session.commit()
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_b.id}/approve",
        json={"payload_sha256": draft_b.payload_sha256, "idempotency_key": "cap-attempt"},
    )
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "send_daily_cap"
    audit = mail_send_audit.get_by_idempotency_key(db_session, "cap-attempt")
    assert audit is not None
    assert audit.send_failed is True
    assert audit.error_code == "send_daily_cap"


class _CaptureTransport:
    def __init__(self, *, rfc_message_id: str | None = "<fixture@example.test>") -> None:
        self.last_json: dict | None = None
        self.rfc_message_id = rfc_message_id

    def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
        if "oauth2.googleapis.com/token" in url:
            return httpx.Response(200, json={"access_token": "tok"})
        if method.upper() == "GET" and "/messages/" in url:
            headers = []
            if self.rfc_message_id:
                headers.append({"name": "Message-ID", "value": self.rfc_message_id})
            return httpx.Response(200, json={"id": "meta", "payload": {"headers": headers}})
        self.last_json = kwargs.get("json")
        return httpx.Response(200, json={"id": "gmail_sent_1"})


def test_approve_send_success_and_double_claim_409(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.com")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())

    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="ops@example.com",
        refresh_token_plaintext="refresh-tok",
        scopes="https://www.googleapis.com/auth/gmail.send",
    )
    db_session.commit()

    draft_id = _seed_draft(db_session, provider_id="msg_send_ok")
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    tx = _CaptureTransport()
    monkeypatch.setattr(mail_hitl, "HttpxTransport", lambda: tx)

    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/approve",
        json={"payload_sha256": draft.payload_sha256, "idempotency_key": "send-once"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"
    assert tx.last_json is not None
    assert tx.last_json.get("threadId") == "thr_hitl_1"
    raw_b64 = str(tx.last_json.get("raw") or "")
    pad = "=" * (-len(raw_b64) % 4)
    msg = message_from_bytes(base64.urlsafe_b64decode(raw_b64 + pad))
    assert msg["In-Reply-To"] == "<fixture@example.test>"
    assert msg["References"] == "<fixture@example.test>"
    assert "Bcc" not in msg
    assert msg["To"] == "demo@example.com"

    resp2 = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/approve",
        json={"payload_sha256": draft.payload_sha256, "idempotency_key": "send-twice"},
    )
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "draft_not_approvable"


def test_approve_idempotent_replay_returns_prior_deny(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same idempotency key returns prior deny/fail outcome without re-send (D-033)."""
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.delenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", raising=False)
    draft_id = _seed_draft(db_session, provider_id="msg_idem_deny")
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    mail_send_audit.insert_audit(
        db_session,
        draft_id=draft_id,
        idempotency_key="idem-deny-replay",
        to_addrs=draft.to_addrs,
        payload_sha256=draft.payload_sha256,
        operator_email="ops@example.com",
        allowlist_denied=True,
        error_code="recipient_not_allowlisted",
    )
    db_session.commit()
    _auth_cookie(api_client)
    resp = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/approve",
        json={"payload_sha256": draft.payload_sha256, "idempotency_key": "idem-deny-replay"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "idempotent_replay"
    assert body.get("allowlist_denied") is True
    assert body.get("send_failed") is False


def test_failed_send_writes_audit_and_failed_status(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.com")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="ops@example.com",
        refresh_token_plaintext="refresh-tok",
        scopes="https://www.googleapis.com/auth/gmail.send",
    )
    draft_id = _seed_draft(db_session, provider_id="msg_fail_send")
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None

    class BoomTransport:
        def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
            if "oauth2.googleapis.com/token" in url:
                return httpx.Response(200, json={"access_token": "tok"})
            if method.upper() == "GET" and "/messages/" in url:
                return httpx.Response(
                    200,
                    json={
                        "id": "meta",
                        "payload": {"headers": [{"name": "Message-ID", "value": "<fail@example.test>"}]},
                    },
                )
            return httpx.Response(500, json={"error": "boom"})

    with pytest.raises(mail_hitl.MailHitlError) as exc:
        mail_hitl.approve_and_send(
            db_session,
            draft_id,
            expected_payload_sha256=draft.payload_sha256,
            operator_email="ops@example.com",
            request_id="req-fail",
            idempotency_key="fail-send-1",
            transport=BoomTransport(),
        )
    assert exc.value.code == "gmail_send_failed"
    refreshed = mail_drafts.get_draft(db_session, draft_id)
    assert refreshed is not None
    assert refreshed.status == "failed"
    audit = mail_send_audit.get_by_idempotency_key(db_session, "fail-send-1")
    assert audit is not None
    assert audit.send_failed is True
    assert audit.error_code == "gmail_send_failed"


def test_error_body_has_code_and_request_id_no_leak(api_client: TestClient, db_session: Session) -> None:
    _auth_cookie(api_client)
    resp = api_client.post(
        "/api/v1/mail/drafts/md_missing/approve",
        json={"payload_sha256": "a" * 64},
        headers={"X-Request-ID": "req-hygiene-1"},
    )
    assert resp.status_code == 404
    err = resp.json()["error"]
    assert err["code"] == "draft_not_found"
    assert err.get("request_id") == "req-hygiene-1"
    blob = resp.text.lower()
    assert "traceback" not in blob


def test_approve_same_idempotency_key_demo_replays(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "1")
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.com")
    draft_id = _seed_draft(db_session, provider_id="msg_idem_demo")
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    _auth_cookie(api_client)
    body = {"payload_sha256": draft.payload_sha256, "idempotency_key": "demo-attempt-1"}
    r1 = api_client.post(f"/api/v1/mail/drafts/{draft_id}/approve", json=body)
    assert r1.status_code == 403
    r2 = api_client.post(f"/api/v1/mail/drafts/{draft_id}/approve", json=body)
    assert r2.status_code == 200
    assert r2.json()["status"] == "idempotent_replay"
    assert r2.json().get("demo_mode_blocked") is True
    from sqlalchemy import text

    n = db_session.execute(
        text("SELECT COUNT(*) FROM mail_send_audit WHERE idempotency_key = 'demo-attempt-1'")
    ).scalar()
    assert int(n or 0) == 1


def test_approve_new_key_after_demo_deny_then_send(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "1")
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.com")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="ops@example.com",
        refresh_token_plaintext="refresh-tok",
        scopes="https://www.googleapis.com/auth/gmail.send",
    )
    db_session.commit()
    draft_id = _seed_draft(db_session, provider_id="msg_idem_retry")
    draft = mail_drafts.get_draft(db_session, draft_id)
    assert draft is not None
    _auth_cookie(api_client)
    deny = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/approve",
        json={"payload_sha256": draft.payload_sha256, "idempotency_key": "key-a"},
    )
    assert deny.status_code == 403
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    tx = _CaptureTransport()
    monkeypatch.setattr(mail_hitl, "HttpxTransport", lambda: tx)
    ok = api_client.post(
        f"/api/v1/mail/drafts/{draft_id}/approve",
        json={"payload_sha256": draft.payload_sha256, "idempotency_key": "key-b"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "sent"
