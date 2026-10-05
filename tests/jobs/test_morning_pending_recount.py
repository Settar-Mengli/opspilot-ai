"""M2: ops_jobs.pending is post-drain count after morning drain."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from opspilot.llm.errors import LlmProvidersExhausted
from opspilot.persistence.models import OpsJobRow
from opspilot.persistence.repositories.work_items import count_gmail_untriaged, upsert_by_provider_id


def test_run_morning_pending_is_post_drain(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """After drain triages all items, job.pending is 0 not the pre-drain count."""
    monkeypatch.setattr("opspilot.jobs.morning_run._preflight", lambda: None)
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "1")
    monkeypatch.delenv("OPSPILOT_SIMULATE_GOOGLE_REAUTH", raising=False)
    monkeypatch.setattr("opspilot.jobs.morning_run.notify_morning_outcome", lambda *a, **k: None)

    def _raise_provider(*_a: object, **_k: object) -> None:
        raise LlmProvidersExhausted("test_no_provider")

    monkeypatch.setattr("opspilot.services.drain.complete_structured_raising", _raise_provider)

    for i in range(3):
        upsert_by_provider_id(
            db_session,
            provider_id=f"msg_pend_{i}",
            source_type="gmail",
            subject_or_title=f"Pending recount {i}",
            body_or_description=f"Body {i}",
            sender_or_requester=f"pend{i}@example.test",
            received_at=datetime(2026, 10, 3, 8, i, tzinfo=UTC),
        )
    db_session.commit()
    assert count_gmail_untriaged(db_session) == 3

    from opspilot.jobs.morning_run import run_morning

    assert run_morning(force_override=True) == 0
    db_session.expire_all()

    job = db_session.scalars(select(OpsJobRow).order_by(OpsJobRow.created_at.desc())).first()
    assert job is not None
    assert job.triaged == 3
    assert count_gmail_untriaged(db_session) == 0
    assert job.pending == 0
