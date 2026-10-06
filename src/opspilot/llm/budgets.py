"""UTC-day request/token budgets with atomic upsert + conditional UPDATE."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

# Unset / empty → remote deny in live config (no invented defaults).
_PROVIDER_ENV = {
    "gemini": ("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "OPSPILOT_BUDGET_GEMINI_TOK_DAY"),
    "groq": ("OPSPILOT_BUDGET_GROQ_REQ_DAY", "OPSPILOT_BUDGET_GROQ_TOK_DAY"),
    "mistral": ("OPSPILOT_BUDGET_MISTRAL_REQ_DAY", "OPSPILOT_BUDGET_MISTRAL_TOK_DAY"),
    "cloudflare": ("OPSPILOT_BUDGET_CLOUDFLARE_REQ_DAY", "OPSPILOT_BUDGET_CLOUDFLARE_TOK_DAY"),
    "openrouter": ("OPSPILOT_BUDGET_OPENROUTER_REQ_DAY", "OPSPILOT_BUDGET_OPENROUTER_TOK_DAY"),
    "ollama": ("OPSPILOT_BUDGET_OLLAMA_REQ_DAY", "OPSPILOT_BUDGET_OLLAMA_TOK_DAY"),
}


def utc_budget_day(now: datetime | None = None) -> date:
    """Budget day is UTC (document skew vs Gemini Pacific RPD in runbook)."""
    return (now or datetime.now(UTC)).date()


def _parse_cap(raw: str | None) -> int | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def req_cap(provider: str) -> int | None:
    envs = _PROVIDER_ENV.get(provider.lower())
    if not envs:
        return None
    return _parse_cap(os.environ.get(envs[0]))


def tok_cap(provider: str) -> int | None:
    envs = _PROVIDER_ENV.get(provider.lower())
    if not envs:
        return None
    return _parse_cap(os.environ.get(envs[1]))


def try_consume_request(session: Session, *, provider: str, day: date | None = None) -> bool:
    """Atomically reserve one request against the daily cap.

    1) INSERT … ON CONFLICT DO NOTHING upsert of the counter row
    2) UPDATE … SET req_count = req_count + 1 WHERE req_count < :cap RETURNING …

    Empty RETURNING → budget deny. Unset cap → deny (fail closed live).
    Anthropic skips daily counters (prepaid ledger is SoT).
    """
    if provider.lower() == "anthropic":
        return True
    cap = req_cap(provider)
    if cap is None:
        return False
    if cap <= 0:
        return False

    day_utc = day or utc_budget_day()
    session.execute(
        text(
            """
            INSERT INTO llm_budget_counters (provider, day_utc, req_count, tok_count)
            VALUES (:provider, :day_utc, 0, 0)
            ON CONFLICT (provider, day_utc) DO NOTHING
            """
        ),
        {"provider": provider, "day_utc": day_utc},
    )
    row = session.execute(
        text(
            """
            UPDATE llm_budget_counters
            SET req_count = req_count + 1
            WHERE provider = :provider
              AND day_utc = :day_utc
              AND req_count < :cap
            RETURNING req_count
            """
        ),
        {"provider": provider, "day_utc": day_utc, "cap": cap},
    ).first()
    return row is not None


def add_tokens(session: Session, *, provider: str, tokens: int, day: date | None = None) -> None:
    """Post-call token reconcile (may overshoot tok cap by ≤1 call)."""
    if provider.lower() == "anthropic":
        return
    if tokens <= 0:
        return
    day_utc = day or utc_budget_day()
    session.execute(
        text(
            """
            INSERT INTO llm_budget_counters (provider, day_utc, req_count, tok_count)
            VALUES (:provider, :day_utc, 0, 0)
            ON CONFLICT (provider, day_utc) DO NOTHING
            """
        ),
        {"provider": provider, "day_utc": day_utc},
    )
    session.execute(
        text(
            """
            UPDATE llm_budget_counters
            SET tok_count = tok_count + :tokens
            WHERE provider = :provider AND day_utc = :day_utc
            """
        ),
        {"provider": provider, "day_utc": day_utc, "tokens": tokens},
    )


def tokens_exhausted(session: Session, *, provider: str, day: date | None = None) -> bool:
    """True when tok_count already at/over cap (pre-call soft check)."""
    if provider.lower() == "anthropic":
        return False
    cap = tok_cap(provider)
    if cap is None:
        return True
    if cap <= 0:
        return True
    day_utc = day or utc_budget_day()
    row = session.execute(
        text(
            """
            SELECT tok_count FROM llm_budget_counters
            WHERE provider = :provider AND day_utc = :day_utc
            """
        ),
        {"provider": provider, "day_utc": day_utc},
    ).first()
    if row is None:
        return False
    return int(row[0]) >= cap
