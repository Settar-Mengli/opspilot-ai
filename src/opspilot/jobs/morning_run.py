"""CLI: morning triage job runner (B6 C3).

Usage::

    uv run python -m opspilot.jobs.morning_run [--force]

Env overrides:
    OPSPILOT_MORNING_FORCE=1          same as --force
    OPSPILOT_SIMULATE_GOOGLE_REAUTH=1 skip Google sync, set reauth_needed
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, date, datetime

from dotenv import load_dotenv

logger = logging.getLogger("opspilot.jobs.morning_run")

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

_EXPECTED_ALEMBIC_HEAD = "0010_ops_jobs_corrections_budget"

_REQUIRED_ENV = ("DATABASE_URL",)


class PreflightError(RuntimeError):
    """Fatal preflight check failure — no DB writes should happen."""


def _preflight() -> None:
    """Validate environment before any DB I/O."""
    from opspilot.llm.providers.anthropic import anthropic_enabled

    if anthropic_enabled():
        raise PreflightError("anthropic_enabled")

    for key in ("OPSPILOT_FORCE_RULES", "FORCE_RULES", "OPSPILOT_LLM_DISABLE", "LLM_DISABLE"):
        if os.environ.get(key, "").strip().lower() in {"1", "true", "yes", "on"}:
            raise PreflightError(f"env_block:{key}")

    for key in _REQUIRED_ENV:
        if not os.environ.get(key, "").strip():
            raise PreflightError(f"missing_env:{key}")

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from opspilot.persistence.db import create_engine, create_session_factory, get_database_url

    cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "alembic.ini")
    cfg = Config(cfg_path)
    script = ScriptDirectory.from_config(cfg)
    repo_head = script.get_current_head()

    engine = create_engine(get_database_url())
    factory = create_session_factory(engine)
    with factory() as session:
        from sqlalchemy import text as sa_text

        db_head = session.execute(sa_text("SELECT version_num FROM alembic_version")).scalar()
    engine.dispose()

    if str(db_head or "") != _EXPECTED_ALEMBIC_HEAD:
        raise PreflightError(f"alembic_head_mismatch expected={_EXPECTED_ALEMBIC_HEAD} db={db_head} repo={repo_head}")


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _google_credential_present(session: Session) -> bool:  # type: ignore[name-defined]  # noqa: F821
    from opspilot.persistence.repositories import oauth_credentials

    cred = oauth_credentials.get_decrypted_refresh(session, provider="google")
    return cred is not None


def _simulate_reauth() -> bool:
    return os.environ.get("OPSPILOT_SIMULATE_GOOGLE_REAUTH", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


# ---------------------------------------------------------------------------
# Telegram notify (C4)
# ---------------------------------------------------------------------------


def notify_morning_outcome(job_id: str, status: str, **meta: object) -> None:
    """Send counts-only Telegram outcome; persist telegram_error_code on HTTP failure."""
    del meta  # counts come from ops_jobs row only (never pass subjects/bodies through meta)
    from opspilot.integrations.telegram_client import fields_from_ops_job, send_outcome_message
    from opspilot.persistence.db import create_engine, create_session_factory, get_database_url
    from opspilot.persistence.models import OpsJobRow
    from opspilot.persistence.repositories.ops_jobs import update_ops_job_fields

    engine = create_engine(get_database_url())
    factory = create_session_factory(engine)
    session = factory()
    try:
        job = session.get(OpsJobRow, job_id)
        if job is None:
            logger.warning("telegram notify skipped missing job_id=%s", job_id)
            return
        fields = fields_from_ops_job(session, job, status=status)
        err = send_outcome_message(fields)
        if err:
            update_ops_job_fields(session, job, telegram_error_code=err)
            session.commit()
            logger.warning("telegram notify failed job=%s code=%s", job_id, err)
        else:
            logger.info("telegram notify ok job=%s status=%s", job_id, status)
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# Corrections-only brief
# ---------------------------------------------------------------------------


def _latest_gmail_run_id(session: Session) -> str | None:  # type: ignore[name-defined]  # noqa: F821
    """Return the most recent run_id that has triage decisions on gmail items."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session as _S  # noqa: F401

    from opspilot.persistence.models import RunArtifactRow, TriageDecisionRow, WorkItemRow

    gmail_run = (
        select(TriageDecisionRow.run_id)
        .join(WorkItemRow, TriageDecisionRow.work_item_id == WorkItemRow.id)
        .where(WorkItemRow.source_type == "gmail")
        .where(TriageDecisionRow.run_id.is_not(None))
        .distinct()
    )
    row = session.execute(
        select(RunArtifactRow.run_id)
        .where(RunArtifactRow.run_id.in_(gmail_run))
        .order_by(RunArtifactRow.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is not None:
        return str(row)
    # Fallback: any run with gmail triage decisions.
    from sqlalchemy import desc

    rid = session.execute(
        select(TriageDecisionRow.run_id)
        .join(WorkItemRow, TriageDecisionRow.work_item_id == WorkItemRow.id)
        .where(WorkItemRow.source_type == "gmail")
        .where(TriageDecisionRow.run_id.is_not(None))
        .order_by(desc(TriageDecisionRow.id))
        .limit(1)
    ).scalar_one_or_none()
    return str(rid) if rid is not None else None


def _last_brief_start(session: Session, run_id: str) -> datetime | None:  # type: ignore[name-defined]  # noqa: F821
    """Start clock of the last job that wrote a brief for ``run_id``.

    Uses COALESCE(ops_jobs.started_at, ops_jobs.created_at) for succeeded/partial
    jobs that recorded ``run_id`` (true no-ops leave run_id null and never mark).
    When no such ops_jobs row exists, falls back to runs.finished_at / runs.started_at
    for pre-ops_jobs briefs only (not GREATEST'd with ops_jobs — that would hide
    mid-window corrections saved before the brief job finished).
    """
    from sqlalchemy import select, text

    from opspilot.persistence.models import RunRow

    job_start_raw = session.execute(
        text(
            """
            SELECT MAX(COALESCE(started_at, created_at))
            FROM ops_jobs
            WHERE run_id = :rid
              AND status IN ('succeeded', 'partial')
            """
        ),
        {"rid": run_id},
    ).scalar()
    # Prefer ops_jobs brief-job start; runs.* only when no ops_jobs marker (pre-B6 briefs).
    if job_start_raw is not None:
        return job_start_raw if isinstance(job_start_raw, datetime) else datetime.fromisoformat(str(job_start_raw))

    run_row = session.execute(select(RunRow).where(RunRow.run_id == run_id)).scalar_one_or_none()
    if run_row is None:
        return None
    candidates: list[datetime] = []
    if run_row.finished_at is not None:
        candidates.append(run_row.finished_at)
    if run_row.started_at is not None:
        candidates.append(run_row.started_at)
    if not candidates:
        return None
    return max(candidates)


def _has_unbriefed_corrections(session: Session, run_id: str) -> bool:  # type: ignore[name-defined]  # noqa: F821
    """True when a triage_corrections.updated_at is newer than last brief start for run_id."""
    from sqlalchemy import func, select

    from opspilot.persistence.models import TriageCorrectionRow

    last_start = _last_brief_start(session, run_id)
    stmt = select(func.count()).select_from(TriageCorrectionRow)
    if last_start is not None:
        stmt = stmt.where(TriageCorrectionRow.updated_at > last_start)
    n = session.execute(stmt).scalar()
    return int(n or 0) > 0


def _upsert_corrections_brief(
    session: Session,  # type: ignore[name-defined]  # noqa: F821
    run_id: str,
) -> str | None:
    """Regenerate the daily briefing on an existing run (corrections-only path)."""
    from sqlalchemy import select

    from opspilot.nlp.action_extractor import extract_action_items
    from opspilot.nlp.briefing_generator import generate_daily_briefing
    from opspilot.persistence.models import RunArtifactRow, TriageDecisionRow, WorkItemRow

    decisions = session.scalars(select(TriageDecisionRow).where(TriageDecisionRow.run_id == run_id)).all()
    if not decisions:
        return None

    from opspilot.models.schemas import TriageRecord, WorkItem

    triage_records: list[TriageRecord] = []
    items: list[WorkItem] = []
    for d in decisions:
        wi = session.get(WorkItemRow, d.work_item_id)
        if wi is None:
            continue
        triage_records.append(
            TriageRecord(
                id=d.work_item_id,
                urgency=d.urgency,
                urgency_reason=d.urgency_reason,
                category=d.category,
                category_reason=d.category_reason,
                sentiment=d.sentiment,
                sentiment_reason=d.sentiment_reason,
                confidence=d.confidence,
                evidence_refs=list(d.evidence_refs or []),
            )
        )
        items.append(
            WorkItem(
                id=wi.id,
                source_type=wi.source_type,
                subject_or_title=wi.subject_or_title,
                body_or_description=wi.body_or_description,
                sender_or_requester=wi.sender_or_requester,
                received_at=wi.received_at,
                tags=wi.tags or [],
            )
        )

    action_items = []
    for item in items:
        action_items.extend(extract_action_items(item))

    run_date = str(date.today())
    briefing = generate_daily_briefing(
        run_date,
        triage_records,
        action_items,
        items,
        current_run_id=run_id,
    )

    # Upsert artifact on existing run.
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(RunArtifactRow).values(
        run_id=run_id,
        name="daily_briefing",
        content_type="text",
        content=briefing,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_run_artifacts_run_name",
        set_={"content": stmt.excluded.content, "content_type": stmt.excluded.content_type},
    )
    session.execute(stmt)
    session.flush()
    return briefing


# ---------------------------------------------------------------------------
# Core morning flow
# ---------------------------------------------------------------------------


def run_morning(*, force_override: bool = False) -> int:
    """Execute the morning job control flow. Returns exit code."""
    from sqlalchemy.orm import Session

    from opspilot.persistence.db import (
        create_engine,
        create_session_factory,
        database_host_label,
        get_database_url,
    )
    from opspilot.persistence.repositories import work_items
    from opspilot.services.drain import DrainResult, drain, morning_request_ceiling
    from opspilot.services.ops_jobs import (
        claim_lease_idle,
        day_claim_morning,
        reap_stale_jobs,
        release_lease,
        takeover_stale_lease,
    )

    # ── 1. Preflight ──
    _preflight()

    # ── 2. Database host label ──
    label = database_host_label()
    print(f"database host={label}")

    # ── Open DB session ──
    engine = create_engine(get_database_url())
    factory = create_session_factory(engine)
    session: Session = factory()
    job_id: str | None = None
    generation: int | None = None

    try:
        # ── 3. Reap stale/orphan jobs ──
        reaped = reap_stale_jobs(session)
        session.commit()
        print(f"reaped={reaped}")

        # ── 4. Day claim ──
        ceiling = morning_request_ceiling()
        job = day_claim_morning(session, force_override=force_override, request_ceiling=ceiling)
        if job is None:
            print("day_claim_blocked (already succeeded/running today)")
            session.commit()
            return 0
        job_id = job.id
        session.commit()
        session.expire_all()
        job = session.get(type(job), job_id)
        assert job is not None
        print(f"job_id={job.id} kind={job.job_kind} force={job.force_override}")

        # ── 5. Lease claim or takeover ──
        generation = claim_lease_idle(session, job.id)
        if generation is None:
            generation = takeover_stale_lease(session, job.id)
        if generation is None:
            # Mark job failed — drain is busy.
            from opspilot.persistence.repositories.ops_jobs import update_ops_job_fields

            update_ops_job_fields(
                session,
                job,
                status="failed",
                error_code="drain_busy",
                finished_at=datetime.now(UTC),
            )
            session.commit()
            print("lease_failed error_code=drain_busy")
            notify_morning_outcome(job.id, "failed", error_code="drain_busy")
            return 1
        session.commit()
        session.expire_all()
        job = session.get(type(job), job_id)
        assert job is not None
        print(f"lease_acquired generation={generation}")

        # ── 6. DEMO_MODE / auth guards ──
        from opspilot.services.operator_session import demo_mode_enabled

        demo = demo_mode_enabled()
        reauth_needed = False
        sync_result: dict[str, object] | None = None

        if _simulate_reauth():
            reauth_needed = True
        elif not demo:
            has_cred = _google_credential_present(session)
            if not has_cred:
                reauth_needed = True

        # ── 7. Sync (if DEMO_MODE=0 and auth OK) ──
        if not demo and not reauth_needed:
            from opspilot.services.google_sync import GoogleReauthRequired, run_sync

            try:
                sync_result = run_sync(session)
                session.commit()
                print(f"sync_ok gmail_upserted={sync_result.get('gmail_upserted', 0)}")
            except GoogleReauthRequired:
                reauth_needed = True
                session.rollback()
                print("sync_reauth_needed")
        elif demo:
            print("sync_skipped reason=demo_mode")
        else:
            print("sync_skipped reason=reauth_needed")

        # Record reauth on the job row.
        if reauth_needed:
            from opspilot.persistence.repositories.ops_jobs import update_ops_job_fields

            update_ops_job_fields(session, job, reauth_needed=True)
            session.flush()

        # Record sync stats on the job row.
        if sync_result is not None:
            from opspilot.persistence.repositories.ops_jobs import update_ops_job_fields

            update_ops_job_fields(
                session,
                job,
                gmail_upserted=int(sync_result.get("gmail_upserted", 0)),  # type: ignore[call-overload]
                gmail_removed=int(sync_result.get("gmail_removed", 0)),  # type: ignore[call-overload]
                calendar_upserted=int(sync_result.get("calendar_upserted", 0)),  # type: ignore[call-overload]
                gmail_truncated=bool(sync_result.get("gmail_truncated", False)),
                calendar_truncated=bool(sync_result.get("calendar_truncated", False)),
            )
            session.flush()

        # ── 8. Count pending ──
        pending = work_items.count_gmail_untriaged(session)
        from opspilot.persistence.repositories.ops_jobs import update_ops_job_fields

        update_ops_job_fields(session, job, pending=pending)
        session.flush()
        print(f"pending={pending}")

        # Detect corrections-only: unbriefed triage_corrections vs last brief start.
        corrections_only = False
        existing_run_id: str | None = None
        if pending == 0:
            existing_run_id = _latest_gmail_run_id(session)
            if existing_run_id is not None and _has_unbriefed_corrections(session, existing_run_id):
                corrections_only = True

        # ── 9. Branch ──
        if pending == 0 and not corrections_only:
            # Zero pending, no unbriefed corrections — true no-op (do not set run_id).
            update_ops_job_fields(
                session,
                job,
                status="succeeded",
                triaged=0,
                finished_at=datetime.now(UTC),
            )
            release_lease(session, job.id, generation)
            session.commit()
            print("zero_pending no_brief succeeded triaged=0")
            notify_morning_outcome(job.id, "succeeded", triaged=0)
            return 0

        if corrections_only:
            assert pending == 0
            assert existing_run_id is not None
            briefing = _upsert_corrections_brief(session, existing_run_id)
            update_ops_job_fields(
                session,
                job,
                status="succeeded",
                triaged=0,
                run_id=existing_run_id,
                finished_at=datetime.now(UTC),
                metadata_json={**job.metadata_json, "brief_reason": "corrections_only"},
            )
            release_lease(session, job.id, generation)
            session.commit()
            print(f"corrections_only run_id={existing_run_id} brief={'yes' if briefing else 'no'}")
            notify_morning_outcome(
                job.id,
                "succeeded",
                triaged=0,
                brief_reason="corrections_only",
            )
            return 0

        # Drain path.
        drain_result: DrainResult = drain(
            session,
            job=job,
            generation=generation,
            ceiling=ceiling,
        )

        # Finalize.
        final_status = "succeeded"
        if drain_result.ceiling_hit or drain_result.budget_exhausted:
            final_status = "partial"

        update_ops_job_fields(
            session,
            job,
            status=final_status,
            triaged=drain_result.triaged,
            request_count=drain_result.request_count,
            rules_fallback_count=drain_result.rules_fallback_count,
            ceiling_hit=drain_result.ceiling_hit,
            budget_exhausted=drain_result.budget_exhausted,
            run_id=drain_result.run_id,
            finished_at=datetime.now(UTC),
        )
        release_lease(session, job.id, generation)
        session.commit()
        print(
            f"drain status={final_status} triaged={drain_result.triaged} "
            f"ceiling_hit={drain_result.ceiling_hit} budget_exhausted={drain_result.budget_exhausted}"
        )
        notify_morning_outcome(
            job.id,
            final_status,
            triaged=drain_result.triaged,
        )
        return 0

    except Exception as original:
        logger.exception("morning_run failed job_id=%s", job_id or "-")
        try:
            session.rollback()
        except Exception:  # noqa: BLE001
            logger.exception("morning_run rollback failed")
        # Cleanup must run even if notify later fails; never mask ``original``.
        try:
            if job_id is not None:
                from opspilot.persistence.models import OpsJobRow
                from opspilot.persistence.repositories.ops_jobs import update_ops_job_fields

                failed_job = session.get(OpsJobRow, job_id)
                if failed_job is not None:
                    update_ops_job_fields(
                        session,
                        failed_job,
                        status="failed",
                        error_code="morning_run_error",
                        finished_at=datetime.now(UTC),
                    )
                    if generation is not None:
                        release_lease(session, job_id, generation)
                    session.commit()
                    try:
                        notify_morning_outcome(job_id, "failed")
                    except Exception:  # noqa: BLE001
                        logger.exception("telegram notify failed during morning failure cleanup")
        except Exception:  # noqa: BLE001
            logger.exception("morning failure cleanup failed job_id=%s", job_id or "-")
        raise original
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m opspilot.jobs.morning_run")
    p.add_argument("--force", action="store_true", help="Force morning job even if today already succeeded.")
    return p


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    force = args.force or os.environ.get("OPSPILOT_MORNING_FORCE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    try:
        return run_morning(force_override=force)
    except PreflightError as exc:
        print(f"PREFLIGHT_FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
