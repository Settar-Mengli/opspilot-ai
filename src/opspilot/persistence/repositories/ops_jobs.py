"""Ops job repository (morning / sync-drain, B6)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from opspilot.persistence.models import OpsJobLeaseRow, OpsJobRow

OPS_JOB_KINDS = frozenset({"morning", "sync_drain"})
OPS_JOB_STATUSES = frozenset({"queued", "running", "succeeded", "partial", "failed", "abandoned", "noop"})
LEASE_SLOT = 1


def new_ops_job_id() -> str:
    return f"oj_{uuid4().hex}"


def insert_ops_job(
    session: Session,
    *,
    job_kind: str,
    day_utc: date | None = None,
    status: str = "queued",
    force_override: bool = False,
    request_ceiling: int = 0,
    run_id: str | None = None,
    metadata_json: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> OpsJobRow:
    if job_kind not in OPS_JOB_KINDS:
        raise ValueError(f"invalid_ops_job_kind:{job_kind}")
    if status not in OPS_JOB_STATUSES:
        raise ValueError(f"invalid_ops_job_status:{status}")
    now = datetime.now(UTC)
    row = OpsJobRow(
        id=job_id or new_ops_job_id(),
        job_kind=job_kind,
        day_utc=day_utc,
        status=status,
        force_override=force_override,
        created_at=now,
        request_ceiling=request_ceiling,
        run_id=run_id,
        metadata_json=metadata_json or {},
    )
    session.add(row)
    session.flush()
    return row


def get_ops_job(session: Session, job_id: str) -> OpsJobRow | None:
    return session.get(OpsJobRow, job_id)


def update_ops_job_fields(session: Session, job: OpsJobRow, **fields: Any) -> OpsJobRow:
    """Patch status, counters, flags, timestamps, and metadata on an ops job."""
    if "status" in fields:
        status = fields["status"]
        if status not in OPS_JOB_STATUSES:
            raise ValueError(f"invalid_ops_job_status:{status}")
    for key, value in fields.items():
        if not hasattr(OpsJobRow, key):
            raise ValueError(f"invalid_ops_job_field:{key}")
        setattr(job, key, value)
    session.flush()
    return job


def get_lease(session: Session) -> OpsJobLeaseRow | None:
    return session.get(OpsJobLeaseRow, LEASE_SLOT)


def upsert_lease(
    session: Session,
    *,
    job_id: str | None,
    heartbeat_at: datetime | None = None,
    generation: int | None = None,
) -> OpsJobLeaseRow:
    row = session.get(OpsJobLeaseRow, LEASE_SLOT)
    if row is None:
        row = OpsJobLeaseRow(
            slot=LEASE_SLOT,
            job_id=job_id,
            heartbeat_at=heartbeat_at,
            generation=generation if generation is not None else 0,
        )
        session.add(row)
    else:
        row.job_id = job_id
        if heartbeat_at is not None:
            row.heartbeat_at = heartbeat_at
        if generation is not None:
            row.generation = generation
    session.flush()
    return row
