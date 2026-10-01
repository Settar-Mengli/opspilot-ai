"""Concurrent approve at daily send cap — advisory lock serializes."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from opspilot.persistence.db import create_engine, create_session_factory
from opspilot.persistence.repositories import mail_drafts, oauth_credentials, work_items
from opspilot.services import mail_hitl


def test_concurrent_approves_at_cap_one_send(
    test_database_url: str, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.com")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_SEND_MAX_PER_DAY", "1")
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

    def _mk(provider_id: str) -> str:
        wi = work_items.upsert_by_provider_id(
            db_session,
            provider_id=provider_id,
            source_type="gmail",
            subject_or_title="Hello",
            body_or_description="Body",
            sender_or_requester="demo@example.com",
            received_at=datetime(2026, 10, 1, tzinfo=UTC),
            thread_id=f"thr_{provider_id}",
        )
        draft = mail_drafts.create_draft(
            db_session,
            work_item_id=wi,
            thread_id=f"thr_{provider_id}",
            gmail_provider_id=provider_id,
            to_addrs="demo@example.com",
            subject="Re: Hello",
            body="Thanks",
            operator_email="ops@example.com",
        )
        return draft.id

    id_a = _mk("msg_cap_a")
    id_b = _mk("msg_cap_b")
    db_session.commit()

    send_count = {"n": 0}
    lock = threading.Lock()

    class CountingTransport:
        def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
            if "oauth2.googleapis.com/token" in url:
                return httpx.Response(200, json={"access_token": "tok"})
            with lock:
                send_count["n"] += 1
                n = send_count["n"]
            return httpx.Response(200, json={"id": f"gmail_{n}"})

    monkeypatch.setattr(mail_hitl, "HttpxTransport", CountingTransport)

    engine = create_engine(test_database_url)
    SessionLocal = create_session_factory(engine)
    results: list[str] = []
    errors: list[str] = []
    barrier = threading.Barrier(2)

    def worker(draft_id: str, key: str) -> None:
        sess = SessionLocal()
        try:
            draft = mail_drafts.get_draft(sess, draft_id)
            assert draft is not None
            barrier.wait(timeout=5)
            try:
                out = mail_hitl.approve_and_send(
                    sess,
                    draft_id,
                    expected_payload_sha256=draft.payload_sha256,
                    operator_email="ops@example.com",
                    request_id=f"req-{key}",
                    idempotency_key=key,
                    transport=CountingTransport(),
                )
                sess.commit()
                results.append(str(out.get("status")))
            except mail_hitl.MailHitlError as exc:
                sess.commit()
                errors.append(exc.code)
        finally:
            sess.close()

    t1 = threading.Thread(target=worker, args=(id_a, "cap-a"))
    t2 = threading.Thread(target=worker, args=(id_b, "cap-b"))
    t1.start()
    t2.start()
    t1.join(timeout=15)
    t2.join(timeout=15)

    assert send_count["n"] == 1
    assert results.count("sent") == 1
    assert "send_daily_cap" in errors
