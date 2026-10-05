"""Hermetic draft_reply + triage id preservation (STOP LIVE 3d)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from opspilot.agent.tools import draft_reply
from opspilot.persistence.models import WorkItemRow
from opspilot.persistence.repositories import work_items
from opspilot.services._llm import compact_triage_lines, format_work_item_id_for_prompt

FULL_WI_ID = "wi_4ebc1679afc94db7a8003bd966e23db7"


def test_format_work_item_id_preserves_35_char_pk() -> None:
    assert len(FULL_WI_ID) == 35
    assert format_work_item_id_for_prompt(FULL_WI_ID) == FULL_WI_ID
    assert format_work_item_id_for_prompt(FULL_WI_ID)[:32] != FULL_WI_ID


def test_compact_triage_lines_preserves_full_work_item_id() -> None:
    text = compact_triage_lines(
        [
            {
                "id": FULL_WI_ID,
                "urgency": "medium",
                "category": "other",
                "urgency_reason": "sync",
            }
        ]
    )
    assert FULL_WI_ID in text
    assert f"{FULL_WI_ID}|" in text


def _seed_gmail_item(session: Session) -> WorkItemRow:
    wi_id = work_items.upsert_by_provider_id(
        session,
        provider_id="gmail_msg_draft_test_1",
        source_type="gmail",
        subject_or_title="Project sync",
        body_or_description="Can we meet Friday?",
        sender_or_requester="Nytherra AI <operator@example.test>",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="gmail_thr_draft_test_1",
    )
    session.commit()
    row = session.get(WorkItemRow, wi_id)
    assert row is not None
    return row


def test_draft_reply_not_found_on_truncated_id(db_session: Session) -> None:
    row = _seed_gmail_item(db_session)
    full = row.id
    assert len(full) == 35
    truncated = full[:32]
    assert db_session.get(WorkItemRow, truncated) is None
    result = draft_reply.run(
        session=db_session,
        args={"work_item_id": truncated, "subject": "Re: Project sync", "body": "Friday works."},
        gmail_only=True,
        operator_email="operator@example.test",
        request_id="req-trunc-1",
    )
    assert result == {"ok": False, "error": "not_found"}


def test_draft_reply_rejects_provider_id_as_pk(db_session: Session) -> None:
    row = _seed_gmail_item(db_session)
    bad = draft_reply.run(
        session=db_session,
        args={
            "work_item_id": row.provider_id,
            "subject": "Re: Project sync",
            "body": "Friday works.",
        },
        gmail_only=True,
        operator_email="operator@example.test",
        request_id="req-pid-1",
    )
    assert bad == {"ok": False, "error": "not_found"}
    good = draft_reply.run(
        session=db_session,
        args={"id": row.id, "subject": "Re: Project sync", "body": "Friday works."},
        gmail_only=True,
        operator_email="operator@example.test",
        request_id="req-pid-2",
    )
    assert good.get("ok") is True
    assert good.get("draft_id")
    assert good.get("to_addrs") == "operator@example.test"


def test_draft_reply_self_sent_derives_operator_to_addrs(db_session: Session) -> None:
    """Reply-to-self is allowed at draft time; allowlist is approve/send only."""
    row = _seed_gmail_item(db_session)
    result = draft_reply.run(
        session=db_session,
        args={"work_item_id": row.id, "subject": "Re: Project sync", "body": "Confirmed."},
        gmail_only=True,
        operator_email="operator@example.test",
        request_id="req-self-1",
    )
    assert result.get("ok") is True
    assert result.get("to_addrs") == "operator@example.test"
