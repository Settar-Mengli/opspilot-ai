"""Shared helpers for LLM-backed services (X4 minimization)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from opspilot.llm.gateway import session_attempt_recorder
from opspilot.llm.policy import llm_allowed
from opspilot.llm.providers.base import LlmProvider
from opspilot.llm.routed import BudgetAwareGateway
from opspilot.llm.routing import build_providers
from opspilot.llm.types import CompletionResult, Message, TaskName

logger = logging.getLogger(__name__)

_MAX_ITEMS = 20
_MAX_REASON_CHARS = 120


def compact_triage_lines(records: list[dict[str, Any]], *, include_title: bool = False) -> str:
    """X4-minimized triage context (fictional IDs / short reasons only)."""
    if not records:
        return "queue: empty"
    lines = [f"queue: {min(len(records), _MAX_ITEMS)} items"]
    for record in records[:_MAX_ITEMS]:
        item_id = str(record.get("id", "?"))[:32]
        urgency = str(record.get("urgency", "?"))[:16]
        category = str(record.get("category", "?"))[:24]
        reason = str(record.get("urgency_reason", ""))[:_MAX_REASON_CHARS]
        if include_title:
            title = str(record.get("subject_or_title", ""))[:60]
            lines.append(f"{item_id}|{urgency}|{category}|{title}|{reason}")
        else:
            lines.append(f"{item_id}|{urgency}|{category}|{reason}")
    return "\n".join(lines)


def providers_or_empty() -> list[LlmProvider]:
    return build_providers()


def complete_prose(
    *,
    task: TaskName,
    system: str,
    user: str,
    max_tokens: int,
    session: Session | None = None,
) -> CompletionResult | None:
    """Run budget-aware complete; return None on policy/empty/exhaustion."""
    if not llm_allowed():
        return None
    providers = providers_or_empty()
    if not providers:
        return None
    recorder = session_attempt_recorder(session) if session is not None else None
    gw = BudgetAwareGateway(providers, session=session, recorder=recorder, observe=True)
    try:
        return gw.complete(
            task=task,
            messages=[Message(role="system", content=system), Message(role="user", content=user)],
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001 — soft-200 at service boundary
        logger.exception("LLM %s failed: %s", task, exc)
        return None
