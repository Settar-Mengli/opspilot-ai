"""Optional Re: subject + reply-subject stacking."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from opspilot.agent.tools.draft_reply import reply_subject_from_original, run
from opspilot.persistence.models import WorkItemRow
from opspilot.persistence.repositories import work_items
from opspilot.services.mail_address import MailAddressError


def test_reply_subject_no_re_stacking() -> None:
    assert reply_subject_from_original("Project sync") == "Re: Project sync"
    assert reply_subject_from_original("Re: Project sync") == "Re: Project sync"
    assert reply_subject_from_original("RE: re: Hello") == "Re: Hello"
    try:
        reply_subject_from_original("Bad\nSubject")
        raise AssertionError("expected MailAddressError")
    except MailAddressError as exc:
        assert exc.code == "unsafe_subject"


def test_draft_reply_derives_subject_when_absent(db_session: Session) -> None:
    wi_id = work_items.upsert_by_provider_id(
        db_session,
        provider_id="gmail_msg_subj_1",
        source_type="gmail",
        subject_or_title="Project sync",
        body_or_description="Body",
        sender_or_requester="other@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_subj_1",
    )
    db_session.commit()
    result = run(
        session=db_session,
        args={"work_item_id": wi_id, "body": "Friday works."},
        gmail_only=True,
        operator_email="ops@example.com",
        request_id="req-subj-1",
    )
    assert result.get("ok") is True
    assert result.get("subject") == "Re: Project sync"


def test_draft_reply_ignores_model_subject(db_session: Session) -> None:
    wi_id = work_items.upsert_by_provider_id(
        db_session,
        provider_id="gmail_msg_subj_ignore_1",
        source_type="gmail",
        subject_or_title="Project Sync",
        body_or_description="Body",
        sender_or_requester="other@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_subj_ignore_1",
    )
    db_session.commit()
    result = run(
        session=db_session,
        args={
            "work_item_id": wi_id,
            "subject": "Follow-up: Project Sync",
            "body": "Friday works.",
        },
        gmail_only=True,
        operator_email="ops@example.com",
        request_id="req-subj-ignore-1",
    )
    assert result.get("ok") is True
    assert result.get("subject") == "Re: Project Sync"


def test_draft_reply_missing_body(db_session: Session) -> None:
    wi_id = work_items.upsert_by_provider_id(
        db_session,
        provider_id="gmail_msg_body_1",
        source_type="gmail",
        subject_or_title="S",
        body_or_description="B",
        sender_or_requester="a@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_body_1",
    )
    db_session.commit()
    assert db_session.get(WorkItemRow, wi_id) is not None
    result = run(
        session=db_session,
        args={"work_item_id": wi_id, "subject": "Re: S"},
        gmail_only=True,
        operator_email="ops@example.com",
        request_id="req-body-1",
    )
    assert result == {"ok": False, "error": "missing_body"}
