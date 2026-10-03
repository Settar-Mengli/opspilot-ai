"""Morning job Telegram notify after commit (H9)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
import pytest
from sqlalchemy.orm import Session

from opspilot.jobs.morning_run import notify_morning_outcome
from opspilot.persistence.models import OpsJobRow, RunRow, TriageDecisionRow
from opspilot.persistence.repositories.ops_jobs import insert_ops_job, update_ops_job_fields
from opspilot.persistence.repositories.work_items import upsert_by_provider_id

_SENSITIVE_MARKERS = (
    "SECRET_SUBJECT_LINE_XYZ",
    "SECRET_BODY_PARAGRAPH_ABC",
    "secret.sender@evil.example",
    "Corr test",
    "Body 0",
)


class _FailTransport:
    def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(503, text="unavailable")


def _seed_gmail_with_sensitive_content(session: Session, *, run_id: str) -> None:
    session.add(RunRow(run_id=run_id, started_at=datetime(2026, 10, 2, 9, tzinfo=UTC), status="success"))
    session.flush()
    wid = upsert_by_provider_id(
        session,
        provider_id="msg_tg_sensitive",
        source_type="gmail",
        subject_or_title="SECRET_SUBJECT_LINE_XYZ",
        body_or_description="SECRET_BODY_PARAGRAPH_ABC",
        sender_or_requester="secret.sender@evil.example",
        received_at=datetime(2026, 10, 2, 9, 0, tzinfo=UTC),
    )
    session.add(
        TriageDecisionRow(
            work_item_id=wid,
            run_id=run_id,
            urgency="high",
            urgency_reason="fixture reason must not appear in telegram",
            category="task",
            category_reason="x",
            sentiment="neutral",
            sentiment_reason="x",
            confidence=0.9,
            evidence_refs=[wid],
        )
    )
    session.flush()


def test_telegram_failure_after_commit(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Committed job status unchanged when Telegram HTTP fails; error code persisted."""
    run_id = "run-tg-fail-001"
    _seed_gmail_with_sensitive_content(db_session, run_id=run_id)
    job = insert_ops_job(db_session, job_kind="morning", day_utc=date(2026, 10, 3), request_ceiling=60)
    update_ops_job_fields(
        db_session,
        job,
        status="succeeded",
        triaged=1,
        pending=0,
        run_id=run_id,
        finished_at=datetime.now(UTC),
    )
    db_session.commit()
    job_id = job.id

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setattr(
        "opspilot.integrations.telegram_client.HttpxTelegramTransport",
        lambda *a, **kw: _FailTransport(),
    )

    notify_morning_outcome(job_id, "succeeded")

    db_session.expire_all()
    row = db_session.get(OpsJobRow, job_id)
    assert row is not None
    assert row.status == "succeeded"
    assert row.triaged == 1
    assert row.telegram_error_code == "http_503"


def test_telegram_message_excludes_sensitive_fixture_fields(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Notify payload is counts-only; never includes subject/body/sender from DB fixtures."""
    run_id = "run-tg-privacy-001"
    _seed_gmail_with_sensitive_content(db_session, run_id=run_id)
    job = insert_ops_job(db_session, job_kind="morning", day_utc=date(2026, 10, 3), request_ceiling=60)
    update_ops_job_fields(
        db_session,
        job,
        status="partial",
        triaged=1,
        pending=2,
        run_id=run_id,
        ceiling_hit=True,
        finished_at=datetime.now(UTC),
    )
    db_session.commit()

    captured: list[str] = []

    class _CaptureTransport:
        def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
            body = kwargs.get("json") or {}
            captured.append(str(body.get("text", "")))
            return httpx.Response(200, json={"ok": True})

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setattr(
        "opspilot.integrations.telegram_client.HttpxTelegramTransport",
        lambda *a, **kw: _CaptureTransport(),
    )

    notify_morning_outcome(job.id, "partial")

    assert len(captured) == 1
    text = captured[0]
    for marker in _SENSITIVE_MARKERS:
        assert marker not in text
    assert "urgency_C/H/M/L=0/1/0/0" in text
    assert "ceiling_hit=true" in text
    assert "fixture reason" not in text
