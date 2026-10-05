"""Corrections-only: brief only when unbriefed triage_corrections exist."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from opspilot.persistence.models import (
    OpsJobRow,
    RunArtifactRow,
    RunRow,
    TriageCorrectionRow,
    TriageDecisionRow,
)
from opspilot.persistence.repositories import triage_corrections
from opspilot.persistence.repositories.work_items import count_gmail_untriaged, upsert_by_provider_id


def _seed_triaged_gmail_item(session: Session, *, run_id: str, idx: int = 0) -> str:
    """Insert a gmail work item with a triage decision on it."""
    wid = upsert_by_provider_id(
        session,
        provider_id=f"msg_corr_{idx}",
        source_type="gmail",
        subject_or_title=f"Corr test {idx}",
        body_or_description=f"Body {idx}",
        sender_or_requester=f"corr{idx}@example.test",
        received_at=datetime(2026, 10, 2, 9, idx, tzinfo=UTC),
    )

    session.add(
        TriageDecisionRow(
            work_item_id=wid,
            run_id=run_id,
            urgency="medium",
            urgency_reason="test",
            category="task",
            category_reason="test",
            sentiment="neutral",
            sentiment_reason="test",
            confidence=0.9,
            evidence_refs=[wid],
        )
    )
    session.flush()
    return wid


def _patch_run_morning_hermetic(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Skip preflight/sync/Telegram; capture notify calls. Returns notify log."""
    notify_log: list[tuple[str, str]] = []

    monkeypatch.setattr("opspilot.jobs.morning_run._preflight", lambda: None)
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "1")
    monkeypatch.delenv("OPSPILOT_SIMULATE_GOOGLE_REAUTH", raising=False)
    # Autouse sets FORCE_RULES; preflight is patched so it is harmless.

    def _capture(job_id: str, status: str, **meta: object) -> None:
        notify_log.append((job_id, status))

    monkeypatch.setattr("opspilot.jobs.morning_run.notify_morning_outcome", _capture)
    return notify_log


def test_upsert_helper_writes_brief_on_existing_run(db_session: Session) -> None:
    """_upsert_corrections_brief still regenerates artifact on an existing gmail run."""
    run_id = "run-20261002-090000-000"
    db_session.add(RunRow(run_id=run_id, started_at=datetime(2026, 10, 2, 9, tzinfo=UTC), status="success"))
    db_session.flush()

    _seed_triaged_gmail_item(db_session, run_id=run_id, idx=0)
    db_session.commit()

    from opspilot.jobs.morning_run import _latest_gmail_run_id, _upsert_corrections_brief

    assert _latest_gmail_run_id(db_session) == run_id
    briefing = _upsert_corrections_brief(db_session, run_id)
    db_session.commit()
    assert briefing is not None
    artifact = db_session.scalars(
        select(RunArtifactRow).where(RunArtifactRow.run_id == run_id, RunArtifactRow.name == "daily_briefing")
    ).one()
    assert artifact.content == briefing


def test_gmail_run_without_corrections_is_true_noop(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Zero-pending + gmail run + no corrections → true no-op; run_id stays null."""
    _patch_run_morning_hermetic(monkeypatch)
    run_id = "run-20261002-110000-000"
    db_session.add(RunRow(run_id=run_id, started_at=datetime(2026, 10, 2, 11, tzinfo=UTC), status="success"))
    db_session.flush()
    _seed_triaged_gmail_item(db_session, run_id=run_id, idx=1)
    db_session.add(RunArtifactRow(run_id=run_id, name="daily_briefing", content_type="text", content="prior brief"))
    db_session.commit()
    assert count_gmail_untriaged(db_session) == 0

    from opspilot.jobs.morning_run import run_morning

    assert run_morning(force_override=True) == 0
    db_session.expire_all()

    jobs = db_session.scalars(select(OpsJobRow).order_by(OpsJobRow.created_at.desc())).all()
    assert jobs
    job = jobs[0]
    assert job.status == "succeeded"
    assert job.triaged == 0
    assert job.run_id is None
    assert (job.metadata_json or {}).get("brief_reason") != "corrections_only"
    artifact = db_session.scalars(
        select(RunArtifactRow).where(RunArtifactRow.run_id == run_id, RunArtifactRow.name == "daily_briefing")
    ).one()
    assert artifact.content == "prior brief"


def test_unbriefed_correction_rewrites_brief(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Correction newer than last brief start → corrections_only + run_id set."""
    _patch_run_morning_hermetic(monkeypatch)
    run_id = "run-20261002-120000-000"
    t0 = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
    db_session.add(RunRow(run_id=run_id, started_at=t0, finished_at=t0 + timedelta(minutes=5), status="success"))
    db_session.flush()
    wid = _seed_triaged_gmail_item(db_session, run_id=run_id, idx=2)
    db_session.add(RunArtifactRow(run_id=run_id, name="daily_briefing", content_type="text", content="old brief"))
    # Prior brief-writing job start at t0.
    db_session.execute(
        text(
            "INSERT INTO ops_jobs (id, job_kind, day_utc, status, force_override, created_at, "
            "started_at, finished_at, run_id, request_ceiling, metadata_json) "
            "VALUES ('job_prior_brief', 'morning', '2026-10-02', 'succeeded', true, :t0, "
            ":t0, :t1, :rid, 60, '{}'::jsonb)"
        ),
        {"t0": t0, "t1": t0 + timedelta(minutes=5), "rid": run_id},
    )
    corr = triage_corrections.upsert_correction(
        db_session, work_item_id=wid, urgency="high", category="action", sentiment="negative"
    )
    # Ensure correction is after prior brief start.
    corr.updated_at = t0 + timedelta(hours=1)
    db_session.flush()
    db_session.commit()

    from opspilot.jobs.morning_run import run_morning

    assert run_morning(force_override=True) == 0
    db_session.expire_all()

    job = db_session.scalars(
        select(OpsJobRow).where(OpsJobRow.id != "job_prior_brief").order_by(OpsJobRow.created_at.desc())
    ).first()
    assert job is not None
    assert job.run_id == run_id
    assert job.metadata_json.get("brief_reason") == "corrections_only"
    artifact = db_session.scalars(
        select(RunArtifactRow).where(RunArtifactRow.run_id == run_id, RunArtifactRow.name == "daily_briefing")
    ).one()
    assert artifact.content != "old brief"


def test_consecutive_mornings_second_is_noop(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """One correction then two zero-pending mornings: first rewrites, second is true no-op."""
    _patch_run_morning_hermetic(monkeypatch)
    run_id = "run-20261002-130000-000"
    db_session.add(
        RunRow(
            run_id=run_id,
            started_at=datetime(2026, 10, 2, 13, tzinfo=UTC),
            finished_at=datetime(2026, 10, 2, 13, 5, tzinfo=UTC),
            status="success",
        )
    )
    db_session.flush()
    wid = _seed_triaged_gmail_item(db_session, run_id=run_id, idx=3)
    db_session.add(RunArtifactRow(run_id=run_id, name="daily_briefing", content_type="text", content="seed brief"))
    triage_corrections.upsert_correction(
        db_session, work_item_id=wid, urgency="critical", category="action", sentiment="negative"
    )
    db_session.commit()

    from opspilot.jobs.morning_run import run_morning

    assert run_morning(force_override=True) == 0
    db_session.expire_all()
    first = db_session.scalars(select(OpsJobRow).order_by(OpsJobRow.created_at.desc())).first()
    assert first is not None
    assert first.run_id == run_id
    assert first.metadata_json.get("brief_reason") == "corrections_only"
    brief_after_first = (
        db_session.scalars(
            select(RunArtifactRow).where(RunArtifactRow.run_id == run_id, RunArtifactRow.name == "daily_briefing")
        )
        .one()
        .content
    )

    assert run_morning(force_override=True) == 0
    db_session.expire_all()
    jobs = db_session.scalars(select(OpsJobRow).order_by(OpsJobRow.created_at.desc())).all()
    assert len(jobs) >= 2
    second = jobs[0]
    assert second.id != first.id
    assert second.status == "succeeded"
    assert second.run_id is None
    assert (second.metadata_json or {}).get("brief_reason") != "corrections_only"
    brief_after_second = (
        db_session.scalars(
            select(RunArtifactRow).where(RunArtifactRow.run_id == run_id, RunArtifactRow.name == "daily_briefing")
        )
        .one()
        .content
    )
    assert brief_after_second == brief_after_first


def test_mid_window_correction_briefed_next_run(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Correction updated_at between brief job start and finish is briefed by the next run."""
    _patch_run_morning_hermetic(monkeypatch)
    run_id = "run-20261002-140000-000"
    t_start = datetime(2026, 10, 2, 14, 0, tzinfo=UTC)
    t_mid = t_start + timedelta(minutes=2)
    t_end = t_start + timedelta(minutes=10)
    db_session.add(RunRow(run_id=run_id, started_at=t_start, finished_at=t_end, status="success"))
    db_session.flush()
    wid = _seed_triaged_gmail_item(db_session, run_id=run_id, idx=4)
    db_session.add(
        RunArtifactRow(run_id=run_id, name="daily_briefing", content_type="text", content="during-job brief")
    )
    db_session.execute(
        text(
            "INSERT INTO ops_jobs (id, job_kind, day_utc, status, force_override, created_at, "
            "started_at, finished_at, run_id, request_ceiling, metadata_json) "
            "VALUES ('job_mid_window', 'morning', '2026-10-02', 'succeeded', true, :t0, "
            ':t0, :t1, :rid, 60, \'{"brief_reason": "corrections_only"}\'::jsonb)'
        ),
        {"t0": t_start, "t1": t_end, "rid": run_id},
    )
    triage_corrections.upsert_correction(
        db_session, work_item_id=wid, urgency="high", category="fyi", sentiment="neutral"
    )
    row = db_session.get(TriageCorrectionRow, wid)
    assert row is not None
    row.updated_at = t_mid
    db_session.flush()
    db_session.commit()

    from opspilot.jobs.morning_run import _has_unbriefed_corrections, run_morning

    assert _has_unbriefed_corrections(db_session, run_id) is True
    assert run_morning(force_override=True) == 0
    db_session.expire_all()
    job = db_session.scalars(
        select(OpsJobRow).where(OpsJobRow.id != "job_mid_window").order_by(OpsJobRow.created_at.desc())
    ).first()
    assert job is not None
    assert job.run_id == run_id
    assert job.metadata_json.get("brief_reason") == "corrections_only"
    artifact = db_session.scalars(
        select(RunArtifactRow).where(RunArtifactRow.run_id == run_id, RunArtifactRow.name == "daily_briefing")
    ).one()
    assert artifact.content != "during-job brief"
