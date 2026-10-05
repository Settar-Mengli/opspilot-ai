"""Telegram bot notifications for morning job outcomes (counts-only, B6 C4)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import httpx

logger = logging.getLogger("opspilot.integrations.telegram")

_TELEGRAM_API = "https://api.telegram.org"


class TelegramTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response: ...


class HttpxTelegramTransport:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        client = self._client or httpx.Client(timeout=30.0)
        owns = self._client is None
        try:
            return client.request(method, url, headers=headers, params=params, data=data, json=json)
        finally:
            if owns:
                client.close()


@dataclass(frozen=True)
class MorningOutcomeFields:
    """Counts and flags only — never titles, bodies, links, or hostnames."""

    status: str
    day_utc: date
    gmail_upserted: int = 0
    gmail_removed: int = 0
    calendar_upserted: int = 0
    triaged: int = 0
    pending: int = 0
    urgency_critical: int = 0
    urgency_high: int = 0
    urgency_medium: int = 0
    urgency_low: int = 0
    rules_fallback_count: int = 0
    ceiling_hit: bool = False
    budget_exhausted: bool = False
    gmail_truncated: bool = False
    calendar_truncated: bool = False
    reauth_needed: bool = False
    forced: bool = False
    error_code: str | None = None


def _env_bot_token() -> str | None:
    raw = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    return raw or None


def _env_chat_id() -> str | None:
    raw = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return raw or None


def _urgency_counts_for_run(session: Any, run_id: str | None) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    if not run_id:
        return counts
    from sqlalchemy import func, select

    from opspilot.persistence.models import TriageDecisionRow

    rows = session.execute(
        select(TriageDecisionRow.urgency, func.count())
        .where(TriageDecisionRow.run_id == run_id)
        .group_by(TriageDecisionRow.urgency)
    ).all()
    for urgency, n in rows:
        key = str(urgency or "").lower()
        if key in counts:
            counts[key] = int(n)
    return counts


def fields_from_ops_job(session: Any, job: Any, *, status: str | None = None) -> MorningOutcomeFields:
    """Build notify payload from a persisted ops_jobs row."""
    eff_status = status if status is not None else str(job.status)
    error_code = job.error_code
    if error_code is not None:
        error_code = str(error_code)

    urg = _urgency_counts_for_run(session, job.run_id)
    return MorningOutcomeFields(
        status=eff_status,
        day_utc=job.day_utc,
        gmail_upserted=int(job.gmail_upserted),
        gmail_removed=int(job.gmail_removed),
        calendar_upserted=int(job.calendar_upserted),
        triaged=int(job.triaged),
        pending=int(job.pending),
        urgency_critical=urg["critical"],
        urgency_high=urg["high"],
        urgency_medium=urg["medium"],
        urgency_low=urg["low"],
        rules_fallback_count=int(job.rules_fallback_count),
        ceiling_hit=bool(job.ceiling_hit),
        budget_exhausted=bool(job.budget_exhausted),
        gmail_truncated=bool(job.gmail_truncated),
        calendar_truncated=bool(job.calendar_truncated),
        reauth_needed=bool(job.reauth_needed),
        forced=bool(job.force_override),
        error_code=error_code,
    )


def format_outcome_message(fields: MorningOutcomeFields) -> str:
    """Plain-text counts-only message (plan §12)."""
    lines = [
        f"status={fields.status}",
        f"day_utc={fields.day_utc.isoformat()}",
        f"gmail_upserted={fields.gmail_upserted}",
        f"gmail_removed={fields.gmail_removed}",
        f"calendar_upserted={fields.calendar_upserted}",
        f"triaged={fields.triaged}",
        f"pending={fields.pending}",
        (
            f"urgency_C/H/M/L={fields.urgency_critical}/{fields.urgency_high}/"
            f"{fields.urgency_medium}/{fields.urgency_low}"
        ),
        f"rules_fallback_count={fields.rules_fallback_count}",
        f"ceiling_hit={str(fields.ceiling_hit).lower()}",
        f"budget_exhausted={str(fields.budget_exhausted).lower()}",
        f"gmail_truncated={str(fields.gmail_truncated).lower()}",
        f"calendar_truncated={str(fields.calendar_truncated).lower()}",
        f"reauth_needed={str(fields.reauth_needed).lower()}",
        f"forced={str(fields.forced).lower()}",
    ]
    if fields.error_code:
        lines.insert(1, f"error_code={fields.error_code}")
    return "\n".join(lines)


def send_outcome_message(
    fields: MorningOutcomeFields,
    *,
    transport: TelegramTransport | None = None,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> str | None:
    """Send outcome to Telegram. Returns telegram_error_code on failure, else None."""
    token = bot_token if bot_token is not None else _env_bot_token()
    chat = chat_id if chat_id is not None else _env_chat_id()
    if not token or not chat:
        logger.info("telegram notify skipped (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID unset)")
        return None

    text = format_outcome_message(fields)
    url = f"{_TELEGRAM_API}/bot{token}/sendMessage"
    tx = transport or HttpxTelegramTransport()
    try:
        resp = tx.request(
            "POST",
            url,
            json={"chat_id": chat, "text": text},
        )
    except httpx.HTTPError:
        logger.warning("telegram notify network error", exc_info=True)
        return "telegram_network_error"

    if resp.status_code >= 400:
        logger.warning("telegram notify http status=%s", resp.status_code)
        return f"http_{resp.status_code}"

    try:
        body = resp.json()
    except ValueError:
        return "telegram_invalid_response"

    if not isinstance(body, dict) or not body.get("ok"):
        return "telegram_api_error"

    return None
