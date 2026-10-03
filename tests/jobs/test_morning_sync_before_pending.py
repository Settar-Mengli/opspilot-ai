"""Sync-before-pending: sync runs even when pending was zero, then triages new items."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from opspilot.persistence.models import OpsJobRow
from opspilot.persistence.repositories.work_items import count_gmail_untriaged, upsert_by_provider_id
from opspilot.services.ops_jobs import claim_lease_idle, day_claim_morning


def test_sync_inserts_items_then_drain_triages(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulates: sync upserts gmail items, then drain processes them."""
    # Initially zero pending.
    assert count_gmail_untriaged(db_session) == 0

    # Simulate sync adding items (what run_sync would do).
    for i in range(3):
        upsert_by_provider_id(
            db_session,
            provider_id=f"msg_sync_{i}",
            source_type="gmail",
            subject_or_title=f"Synced item {i}",
            body_or_description=f"Body {i}",
            sender_or_requester=f"sync{i}@example.com",
            received_at=datetime(2026, 10, 3, 8, i, tzinfo=UTC),
        )
    db_session.flush()

    # Now pending > 0.
    assert count_gmail_untriaged(db_session) == 3

    # Set up job + lease.
    job = day_claim_morning(db_session, day_utc=date(2026, 10, 3))
    assert job is not None
    gen = claim_lease_idle(db_session, job.id)
    assert gen is not None
    db_session.commit()
    db_session.expire_all()
    job = db_session.get(OpsJobRow, job.id)
    assert job is not None

    # Drain should process them.
    # Patch LLM to use rules fallback.
    from opspilot.llm.errors import LlmProvidersExhausted
    from opspilot.services.drain import drain

    def _raise_provider(*a: object, **kw: object) -> None:
        raise LlmProvidersExhausted("test_no_provider")

    monkeypatch.setattr("opspilot.services.drain.complete_structured_raising", _raise_provider)

    result = drain(db_session, job=job, generation=gen, ceiling=60, heartbeat_interval_s=9999)
    db_session.commit()

    assert result.triaged == 3
    assert result.rules_fallback_count == 3


def test_sync_order_is_before_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the control flow calls sync before counting pending."""
    # This is a structural test — we check that run_morning's flow order is:
    # sync → count_pending (not count → sync).
    # We verify by inspecting the source code order.
    import inspect

    from opspilot.jobs.morning_run import run_morning

    source = inspect.getsource(run_morning)
    sync_pos = source.find("run_sync")
    count_pos = source.find("count_gmail_untriaged")
    assert sync_pos > 0, "run_sync not found in run_morning"
    assert count_pos > 0, "count_gmail_untriaged not found in run_morning"
    assert sync_pos < count_pos, "sync must come before count_pending in control flow"
