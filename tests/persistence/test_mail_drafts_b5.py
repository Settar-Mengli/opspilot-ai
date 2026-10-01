"""Mail draft + send audit repos (B5 / 0008)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from opspilot.persistence.repositories import mail_drafts, mail_send_audit


def test_create_draft_and_update_subject_body(db_session: Session) -> None:
    draft = mail_drafts.create_draft(
        db_session,
        work_item_id=None,
        thread_id="thr_1",
        gmail_provider_id="msg_1",
        to_addrs="demo@example.com",
        subject="Hello",
        body="World",
        operator_email="ops@example.com",
    )
    assert draft.id.startswith("md_")
    assert draft.status == "draft"
    old_hash = draft.payload_sha256

    mail_drafts.update_subject_body(db_session, draft, subject="Hello2", body="World2")
    assert draft.subject == "Hello2"
    assert draft.body == "World2"
    assert draft.payload_sha256 != old_hash
    assert draft.to_addrs == "demo@example.com"
    assert draft.thread_id == "thr_1"


def test_send_audit_idempotency_unique(db_session: Session) -> None:
    draft = mail_drafts.create_draft(
        db_session,
        work_item_id=None,
        thread_id="thr_2",
        gmail_provider_id="msg_2",
        to_addrs="demo@example.com",
        subject="S",
        body="B",
    )
    row = mail_send_audit.insert_audit(
        db_session,
        draft_id=draft.id,
        idempotency_key="idem-1",
        to_addrs=draft.to_addrs,
        payload_sha256=draft.payload_sha256,
        operator_email="ops@example.com",
    )
    assert row.id > 0
    found = mail_send_audit.get_by_idempotency_key(db_session, "idem-1")
    assert found is not None
    assert found.draft_id == draft.id
