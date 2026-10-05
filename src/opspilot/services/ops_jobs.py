"""Job lifecycle helpers for pooler-safe Postgres (B6 C2).

Reap / lease / fence / drain primitives. All functions take an open
SQLAlchemy ``Session``; callers own commit boundaries.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from opspilot.persistence.models import OpsJobRow
from opspilot.persistence.repositories.ops_jobs import (
    LEASE_SLOT,
    new_ops_job_id,
)

# ---------------------------------------------------------------------------
# Environment thresholds
# ---------------------------------------------------------------------------

_DEFAULT_HEARTBEAT_S = 15
_DEFAULT_STALE_S = 900
_DEFAULT_QUEUED_ORPHAN_S = 120


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def heartbeat_seconds() -> int:
    return _env_int("OPSPILOT_JOB_HEARTBEAT_SECONDS", _DEFAULT_HEARTBEAT_S)


def stale_seconds() -> int:
    return _env_int("OPSPILOT_JOB_STALE_SECONDS", _DEFAULT_STALE_S)


def queued_orphan_seconds() -> int:
    return _env_int("OPSPILOT_JOB_QUEUED_ORPHAN_SECONDS", _DEFAULT_QUEUED_ORPHAN_S)


# ---------------------------------------------------------------------------
# Reap stale jobs
# ---------------------------------------------------------------------------


def reap_stale_jobs(session: Session) -> int:
    """Abandon stale lease holders and queued orphans; clear lease. Returns count abandoned."""
    stale_s = stale_seconds()
    orphan_s = queued_orphan_seconds()
    # Plan §4.5: one txn — stale holders then orphans not holding the lease.
    abandoned = session.execute(
        text(
            """
            WITH stale_holders AS (
              SELECT l.job_id FROM ops_job_lease l
              WHERE l.slot = 1 AND l.job_id IS NOT NULL
                AND l.heartbeat_at < NOW() - MAKE_INTERVAL(secs => :stale_seconds)
            ),
            abandoned AS (
              UPDATE ops_jobs j SET status='abandoned',
                error_code=COALESCE(j.error_code,'stale_lease'), finished_at=NOW()
              FROM stale_holders s WHERE j.id=s.job_id AND j.status IN ('queued','running')
              RETURNING j.id
            ),
            cleared AS (
              UPDATE ops_job_lease SET job_id=NULL, heartbeat_at=NULL
              WHERE slot=1 AND job_id IN (SELECT id FROM abandoned)
              RETURNING job_id
            ),
            orphans AS (
              UPDATE ops_jobs j SET status='abandoned',
                error_code=COALESCE(j.error_code,'orphaned_no_lease'), finished_at=NOW()
              WHERE j.status IN ('queued','running')
                AND j.created_at < NOW() - MAKE_INTERVAL(secs => :queued_orphan_seconds)
                AND (SELECT l.job_id FROM ops_job_lease l WHERE l.slot=1) IS DISTINCT FROM j.id
              RETURNING j.id
            )
            SELECT (SELECT count(*) FROM abandoned) + (SELECT count(*) FROM orphans) AS n
            """
        ),
        {"stale_seconds": stale_s, "queued_orphan_seconds": orphan_s},
    ).scalar()
    session.flush()
    return int(abandoned or 0)


# ---------------------------------------------------------------------------
# Lease primitives
# ---------------------------------------------------------------------------


class FenceError(Exception):
    """Raised when a lease generation check fails (stale worker)."""


def claim_lease_idle(session: Session, job_id: str) -> int | None:
    """Claim the singleton lease if it is currently idle (no job_id).

    Returns the new generation on success, None if the lease is held.
    """
    now = datetime.now(UTC)
    row = (
        session.execute(
            text("SELECT slot, job_id, generation FROM ops_job_lease WHERE slot = :slot FOR UPDATE"),
            {"slot": LEASE_SLOT},
        )
        .mappings()
        .one_or_none()
    )

    if row is None:
        # First-ever lease row.
        gen = 1
        session.execute(
            text(
                "INSERT INTO ops_job_lease (slot, job_id, heartbeat_at, generation) VALUES (:slot, :job_id, :now, :gen)"
            ),
            {"slot": LEASE_SLOT, "job_id": job_id, "now": now, "gen": gen},
        )
        session.flush()
        return gen

    if row["job_id"] is not None:
        return None  # lease held

    gen = int(row["generation"]) + 1
    session.execute(
        text("UPDATE ops_job_lease SET job_id = :job_id, heartbeat_at = :now, generation = :gen WHERE slot = :slot"),
        {"job_id": job_id, "now": now, "gen": gen, "slot": LEASE_SLOT},
    )
    # Also stamp generation on the job row.
    session.execute(
        text("UPDATE ops_jobs SET lease_generation = :gen, status = 'running', started_at = :now WHERE id = :jid"),
        {"gen": gen, "now": now, "jid": job_id},
    )
    session.flush()
    return gen


def takeover_stale_lease(session: Session, new_job_id: str, *, stale_s: int | None = None) -> int | None:
    """Take over the singleton lease from a stale holder.

    Uses FOR UPDATE on the lease row, abandons the prior job, bumps generation.
    Returns the new generation on success, None if the lease is not stale.
    """
    cutoff_s = stale_s if stale_s is not None else stale_seconds()
    now = datetime.now(UTC)
    cutoff = now - __import__("datetime").timedelta(seconds=cutoff_s)

    row = (
        session.execute(
            text("SELECT slot, job_id, heartbeat_at, generation FROM ops_job_lease WHERE slot = :slot FOR UPDATE"),
            {"slot": LEASE_SLOT},
        )
        .mappings()
        .one_or_none()
    )

    if row is None or row["job_id"] is None:
        return None  # nothing to take over (use claim_lease_idle instead)

    hb = row["heartbeat_at"]
    if hb is not None and hb >= cutoff:
        return None  # not stale

    # Abandon prior job.
    prior_job_id = row["job_id"]
    session.execute(
        text(
            "UPDATE ops_jobs SET status = 'abandoned', error_code = COALESCE(error_code, 'stale_lease'), "
            "finished_at = :now WHERE id = :jid AND status IN ('queued', 'running')"
        ),
        {"now": now, "jid": prior_job_id},
    )

    gen = int(row["generation"]) + 1
    session.execute(
        text("UPDATE ops_job_lease SET job_id = :job_id, heartbeat_at = :now, generation = :gen WHERE slot = :slot"),
        {"job_id": new_job_id, "now": now, "gen": gen, "slot": LEASE_SLOT},
    )
    session.execute(
        text("UPDATE ops_jobs SET lease_generation = :gen, status = 'running', started_at = :now WHERE id = :jid"),
        {"gen": gen, "now": now, "jid": new_job_id},
    )
    session.flush()
    return gen


def heartbeat(session: Session, job_id: str, generation: int) -> bool:
    """Refresh the lease heartbeat. Returns False if generation doesn't match."""
    now = datetime.now(UTC)
    result = session.execute(
        text("UPDATE ops_job_lease SET heartbeat_at = :now WHERE slot = :slot AND job_id = :jid AND generation = :gen"),
        {"now": now, "slot": LEASE_SLOT, "jid": job_id, "gen": generation},
    )
    session.flush()
    return int(getattr(result, "rowcount", 0) or 0) > 0


def release_lease(session: Session, job_id: str, generation: int) -> None:
    """Release the lease if generation matches (clear job_id + heartbeat)."""
    session.execute(
        text(
            "UPDATE ops_job_lease SET job_id = NULL, heartbeat_at = NULL "
            "WHERE slot = :slot AND job_id = :jid AND generation = :gen"
        ),
        {"slot": LEASE_SLOT, "jid": job_id, "gen": generation},
    )
    session.flush()


def fence_check(session: Session, job_id: str, generation: int) -> None:
    """SELECT FOR UPDATE on lease; raise FenceError unless job_id and generation match."""
    row = (
        session.execute(
            text("SELECT job_id, generation FROM ops_job_lease WHERE slot = :slot FOR UPDATE"),
            {"slot": LEASE_SLOT},
        )
        .mappings()
        .one_or_none()
    )

    if row is None or row["job_id"] != job_id or int(row["generation"]) != generation:
        raise FenceError(
            f"fence_check: expected job={job_id} gen={generation}, "
            f"got job={row['job_id'] if row else None} gen={row['generation'] if row else None}"
        )


# ---------------------------------------------------------------------------
# Day claim (morning job idempotency)
# ---------------------------------------------------------------------------


def day_claim_morning(
    session: Session,
    *,
    day_utc: date | None = None,
    request_ceiling: int = 0,
    force_override: bool = False,
) -> OpsJobRow | None:
    """INSERT morning job; ON CONFLICT DO NOTHING on partial unique (non-force).

    Returns the OpsJobRow if inserted, None if blocked by the day unique index.
    Forced rows always insert (partial index excludes force_override=true).
    """
    target_day = day_utc or date.today()
    job_id = new_ops_job_id()
    now = datetime.now(UTC)

    if force_override:
        session.execute(
            text(
                "INSERT INTO ops_jobs (id, job_kind, day_utc, status, force_override, "
                "created_at, request_ceiling, metadata_json) "
                "VALUES (:id, 'morning', :day, 'queued', true, :now, :ceil, '{}'::jsonb)"
            ),
            {"id": job_id, "day": target_day, "now": now, "ceil": request_ceiling},
        )
        session.flush()
        return session.get(OpsJobRow, job_id)

    result = session.execute(
        text(
            "INSERT INTO ops_jobs (id, job_kind, day_utc, status, force_override, "
            "created_at, request_ceiling, metadata_json) "
            "VALUES (:id, 'morning', :day, 'queued', false, :now, :ceil, '{}'::jsonb) "
            "ON CONFLICT (day_utc) WHERE job_kind = 'morning' AND force_override = false "
            "AND status IN ('queued','running','succeeded','partial') DO NOTHING "
            "RETURNING id"
        ),
        {"id": job_id, "day": target_day, "now": now, "ceil": request_ceiling},
    )
    row_id = result.scalar()
    session.flush()
    if row_id is None:
        return None
    return session.get(OpsJobRow, row_id)
