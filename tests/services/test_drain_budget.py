"""Drain budget tests: budget-denied stops without persist; provider errors use rules."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.llm.errors import LlmProvidersExhausted
from opspilot.persistence.models import TriageDecisionRow
from opspilot.persistence.repositories.ops_jobs import insert_ops_job
from opspilot.persistence.repositories.work_items import upsert_by_provider_id
from opspilot.services.drain import drain
from opspilot.services.ops_jobs import claim_lease_idle


def _seed_gmail(session: Session, *, count: int = 3) -> list[str]:
    ids = []
    for i in range(count):
        wid = upsert_by_provider_id(
            session,
            provider_id=f"msg_b_{i}",
            source_type="gmail",
            subject_or_title=f"Budget test {i}",
            body_or_description=f"Body {i}",
            sender_or_requester=f"budget{i}@example.com",
            received_at=datetime(2026, 10, 3, 9, i, tzinfo=UTC),
        )
        ids.append(wid)
    session.flush()
    return ids


def _setup_job_and_lease(session: Session) -> tuple:
    job = insert_ops_job(
        session,
        job_kind="morning",
        day_utc=date(2026, 10, 3),
        request_ceiling=60,
    )
    gen = claim_lease_idle(session, job.id)
    assert gen is not None
    session.commit()
    session.expire_all()
    job = session.get(type(job), job.id)
    return job, gen


def test_all_budget_denied_stops_without_rules_persist(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """When every LLM call is budget-denied, drain stops with zero persisted decisions."""
    _seed_gmail(db_session, count=3)
    job, gen = _setup_job_and_lease(db_session)

    # Patch complete_structured_raising to always raise budget_denied.
    def _raise_budget(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise LlmProvidersExhausted("budget_denied")

    monkeypatch.setattr("opspilot.services.drain.complete_structured_raising", _raise_budget)

    result = drain(
        db_session,
        job=job,
        generation=gen,
        ceiling=60,
        heartbeat_interval_s=9999,
    )
    db_session.commit()

    assert result.triaged == 0
    assert result.budget_exhausted is True
    assert result.rules_fallback_count == 0
    # No decisions persisted.
    count = db_session.scalar(select(func.count()).select_from(TriageDecisionRow))
    assert count == 0


def test_provider_errors_persist_rules_and_count(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """When providers fail (not budget), drain uses rules fallback and persists."""
    _seed_gmail(db_session, count=3)
    job, gen = _setup_job_and_lease(db_session)

    # Patch complete_structured_raising to raise non-budget exhaustion.
    def _raise_provider(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise LlmProvidersExhausted("all providers failed")

    monkeypatch.setattr("opspilot.services.drain.complete_structured_raising", _raise_provider)

    result = drain(
        db_session,
        job=job,
        generation=gen,
        ceiling=60,
        heartbeat_interval_s=9999,
    )
    db_session.commit()

    assert result.triaged == 3
    assert result.rules_fallback_count == 3
    assert result.budget_exhausted is False
    # Decisions persisted via rules.
    count = db_session.scalar(select(func.count()).select_from(TriageDecisionRow))
    assert count == 3
