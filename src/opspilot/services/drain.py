"""Drain loop: triage untriaged gmail items under a request ceiling (B6 C2).

NEVER calls ``execute_pipeline`` or ``triage_connected_gmail*``.
Each item is classified via ``complete_structured_raising`` (LLM) or
rules fallback, persisted with fence, and counted against the ceiling.
After triage, a brief is generated on the same run if any items were triaged.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from opspilot.adapters.gateway_triage import build_triage_user_prompt
from opspilot.adapters.rule_based import RuleBasedAdapter
from opspilot.history.run_history import generate_run_id, utc_now
from opspilot.llm.errors import LlmPolicyDenied, LlmProvidersExhausted
from opspilot.llm.prompt_safety import UNTRUSTED_SYSTEM_POLICY
from opspilot.llm.schemas.triage import TriagePayload
from opspilot.models.schemas import TriageRecord, WorkItem
from opspilot.nlp.action_extractor import extract_action_items
from opspilot.nlp.briefing_generator import generate_daily_briefing
from opspilot.persistence.models import OpsJobRow, RunArtifactRow, RunRow, TriageDecisionRow
from opspilot.persistence.repositories import work_items
from opspilot.services._llm import complete_structured_raising
from opspilot.services.ops_jobs import FenceError, fence_check, heartbeat

logger = logging.getLogger("opspilot.services.drain")

# ---------------------------------------------------------------------------
# Ceilings (env)
# ---------------------------------------------------------------------------

_DEFAULT_MORNING_CEILING = 60
_DEFAULT_SYNC_CEILING = 40
_DEFAULT_BRIEF_RESERVE = 10

_TRIAGE_SYSTEM = (
    "You are an operations triage assistant. Classify the work item. "
    f"{UNTRUSTED_SYSTEM_POLICY} "
    "Include confidence (0-1) and evidence_refs citing only the item id. "
    "Respond with JSON only matching the schema. No markdown."
)
_STRUCTURED_MAX_TOKENS = 1024


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def morning_request_ceiling() -> int:
    return _env_int("OPSPILOT_MORNING_REQUEST_CEILING", _DEFAULT_MORNING_CEILING)


def sync_request_ceiling() -> int:
    return _env_int("OPSPILOT_SYNC_REQUEST_CEILING", _DEFAULT_SYNC_CEILING)


def brief_request_reserve() -> int:
    return _env_int("OPSPILOT_BRIEF_REQUEST_RESERVE", _DEFAULT_BRIEF_RESERVE)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class DrainResult:
    triaged: int = 0
    rules_fallback_count: int = 0
    request_count: int = 0
    ceiling_hit: bool = False
    budget_exhausted: bool = False
    run_id: str | None = None
    briefing_text: str | None = None
    triage_records: list[TriageRecord] = field(default_factory=list)
    items: list[WorkItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Drain
# ---------------------------------------------------------------------------

_BUDGET_ERRORS = frozenset({"budget_denied", "budget_denied_repair", "budget_denied_no_session"})


def _is_budget_denied(exc: LlmProvidersExhausted) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in _BUDGET_ERRORS)


def drain(
    session: Session,
    *,
    job: OpsJobRow,
    generation: int,
    ceiling: int | None = None,
    heartbeat_interval_s: int | None = None,
) -> DrainResult:
    """Triage untriaged gmail items under a request ceiling.

    This is the core drain loop.  It does NOT call ``execute_pipeline``
    or ``triage_connected_gmail*``.
    """
    from opspilot.services.ops_jobs import heartbeat_seconds

    hb_interval = heartbeat_interval_s if heartbeat_interval_s is not None else heartbeat_seconds()
    eff_ceiling = (
        ceiling
        if ceiling is not None
        else (morning_request_ceiling() if job.job_kind == "morning" else sync_request_ceiling())
    )
    reserve = brief_request_reserve()
    drain_limit = max(0, eff_ceiling - reserve)

    result = DrainResult()
    rules_adapter = RuleBasedAdapter()

    # Fetch untriaged items.
    raw_items = work_items.list_gmail_untriaged_raw(session, limit=drain_limit or 1000)
    if not raw_items:
        return result

    # Create a run row for persistence.
    started = utc_now()
    run_id = generate_run_id(started)
    result.run_id = run_id

    last_hb = time.monotonic()

    for raw in raw_items:
        # Heartbeat check.
        now_mono = time.monotonic()
        if hb_interval > 0 and (now_mono - last_hb) >= hb_interval:
            if not heartbeat(session, job.id, generation):
                break  # lost lease
            last_hb = now_mono

        item = WorkItem(
            id=raw["id"],
            source_type=raw["source_type"],
            subject_or_title=raw["subject_or_title"],
            body_or_description=raw["body_or_description"],
            sender_or_requester=raw["sender_or_requester"],
            received_at=raw["received_at"],
            tags=raw.get("tags", []),
        )

        # Attempt LLM classification.
        triage: TriageRecord | None = None
        used_rules = False
        budget_stop = False

        try:
            user_prompt = build_triage_user_prompt(item)
            payload = complete_structured_raising(
                task="triage",
                system=_TRIAGE_SYSTEM,
                user=user_prompt,
                schema=TriagePayload,
                max_tokens=_STRUCTURED_MAX_TOKENS,
                session=session,
            )
            if payload is not None:
                triage = TriageRecord(
                    id=item.id,
                    urgency=payload.urgency,
                    urgency_reason=payload.urgency_reason,
                    category=payload.category,
                    category_reason=payload.category_reason,
                    sentiment=payload.sentiment,
                    sentiment_reason=payload.sentiment_reason,
                    confidence=payload.confidence,
                    evidence_refs=list(payload.evidence_refs),
                )
            else:
                # Soft None from non-budget errors → rules.
                triage = rules_adapter.classify(item)
                used_rules = True
        except (LlmProvidersExhausted, LlmPolicyDenied) as exc:
            if isinstance(exc, LlmProvidersExhausted) and _is_budget_denied(exc):
                result.budget_exhausted = True
                budget_stop = True
            else:
                # Other exhaustion (real provider errors) → rules fallback.
                triage = rules_adapter.classify(item)
                used_rules = True
        except Exception:  # noqa: BLE001
            triage = rules_adapter.classify(item)
            used_rules = True

        if budget_stop:
            # Budget denied: do NOT persist, stop immediately.
            break

        assert triage is not None

        # Persist: fence + decision in same flush.
        try:
            fence_check(session, job.id, generation)
        except FenceError:
            break

        # Ensure run row exists (once).
        if result.triaged == 0:
            _ensure_run_row(session, run_id, started)

        _persist_decision(session, triage, run_id)

        result.triaged += 1
        result.request_count += 1
        if used_rules:
            result.rules_fallback_count += 1
        result.triage_records.append(triage)
        result.items.append(item)

        # Update ops_job counters.
        session.execute(
            text("UPDATE ops_jobs SET triaged = :t, request_count = :r, rules_fallback_count = :rf WHERE id = :jid"),
            {
                "t": result.triaged,
                "r": result.request_count,
                "rf": result.rules_fallback_count,
                "jid": job.id,
            },
        )
        session.flush()

        if drain_limit > 0 and result.request_count >= drain_limit:
            result.ceiling_hit = True
            break

    # Briefing (if we triaged anything).
    if result.triaged > 0:
        result.briefing_text = _generate_briefing(
            session,
            result,
            job,
            generation,
        )

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_run_row(session: Session, run_id: str, started: datetime) -> None:
    session.add(
        RunRow(
            run_id=run_id,
            started_at=started,
            status="running",
        )
    )
    session.flush()


def _persist_decision(session: Session, triage: TriageRecord, run_id: str) -> None:
    session.add(
        TriageDecisionRow(
            work_item_id=triage.id,
            run_id=run_id,
            urgency=triage.urgency,
            urgency_reason=triage.urgency_reason,
            category=triage.category,
            category_reason=triage.category_reason,
            sentiment=triage.sentiment,
            sentiment_reason=triage.sentiment_reason,
            confidence=triage.confidence,
            evidence_refs=triage.evidence_refs,
        )
    )
    session.flush()


def _generate_briefing(
    session: Session,
    result: DrainResult,
    job: OpsJobRow,
    generation: int,
) -> str:
    """Generate rules-based briefing and persist under fence on the drain run."""
    assert result.run_id is not None
    fence_check(session, job.id, generation)
    run_date = str(job.day_utc)
    action_items = []
    for item in result.items:
        action_items.extend(extract_action_items(item))

    briefing = generate_daily_briefing(
        run_date,
        result.triage_records,
        action_items,
        result.items,
        current_run_id=result.run_id,
    )
    session.add(
        RunArtifactRow(
            run_id=result.run_id,
            name="daily_briefing",
            content_type="text",
            content=briefing,
        )
    )
    session.execute(
        text("UPDATE ops_jobs SET run_id = :rid WHERE id = :jid"),
        {"rid": result.run_id, "jid": job.id},
    )
    session.flush()
    return briefing
