"""Shared helpers for LLM-backed services (X4 minimization)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from opspilot.llm.gateway import session_attempt_recorder
from opspilot.llm.meta_redact import redact_text
from opspilot.llm.policy import llm_allowed
from opspilot.llm.providers.base import LlmProvider
from opspilot.llm.routed import BudgetAwareGateway
from opspilot.llm.routing import build_providers
from opspilot.llm.types import CompletionResult, Message, TaskName

logger = logging.getLogger(__name__)


def _resolve_request_id(request_id: str | None) -> str | None:
    if request_id:
        return request_id
    try:
        from opspilot.api.app import request_id_ctx

        return request_id_ctx.get()
    except Exception:  # noqa: BLE001 — app may be unavailable in some CLI contexts
        return None


def _log_llm_failure(task: TaskName, exc: BaseException) -> None:
    code = type(exc).__name__
    msg = redact_text(str(exc), max_chars=200)
    logger.error("LLM %s failed error_code=%s message=%s", task, code, msg)


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


def soft_deny(*, unavailable: str, no_provider: str) -> str | None:
    """Shared soft-deny order: policy → no providers → None if call may proceed.

    When the LLM attempt already failed, callers treat None as ``unavailable``.
    """
    if not llm_allowed():
        return unavailable
    if not providers_or_empty():
        return no_provider
    return None


@contextmanager
def llm_session_scope(session: Session | None = None) -> Iterator[Session | None]:
    """Use injected session, or open a short-lived sync session from DATABASE_URL.

    Yields None when no DB is available (caller must fall back to rules/soft).
    """
    if session is not None:
        yield session
        return
    try:
        from opspilot.persistence.db import create_engine, create_session_factory, get_database_url

        engine = create_engine(get_database_url())
        factory = create_session_factory(engine)
        owned = factory()
    except Exception:  # noqa: BLE001 — fail closed to soft/rules
        logger.debug("llm_session_scope: no database session available", exc_info=True)
        yield None
        return
    try:
        yield owned
        owned.commit()
    except Exception:
        owned.rollback()
        raise
    finally:
        owned.close()
        engine.dispose()


def complete_prose(
    *,
    task: TaskName,
    system: str,
    user: str,
    max_tokens: int,
    session: Session | None = None,
    request_id: str | None = None,
) -> CompletionResult | None:
    """Run budget-aware complete; return None on policy/empty/exhaustion/no-session."""
    if not llm_allowed():
        return None
    providers = providers_or_empty()
    if not providers:
        return None
    with llm_session_scope(session) as scoped:
        if scoped is None:
            return None
        recorder = session_attempt_recorder(scoped)
        gw = BudgetAwareGateway(
            providers,
            session=scoped,
            recorder=recorder,
            observe=True,
            request_id=_resolve_request_id(request_id),
        )
        try:
            return gw.complete(
                task=task,
                messages=[Message(role="system", content=system), Message(role="user", content=user)],
                max_tokens=max_tokens,
            )
        except Exception as exc:  # noqa: BLE001 — soft-200 at service boundary
            _log_llm_failure(task, exc)
            return None


def complete_structured[T: BaseModel](
    *,
    task: TaskName,
    system: str,
    user: str,
    schema: type[T],
    max_tokens: int,
    session: Session | None = None,
    request_id: str | None = None,
) -> T | None:
    """Budget-aware complete_json; None on deny/exhaustion."""
    if not llm_allowed():
        return None
    providers = providers_or_empty()
    if not providers:
        return None
    with llm_session_scope(session) as scoped:
        if scoped is None:
            return None
        recorder = session_attempt_recorder(scoped)
        gw = BudgetAwareGateway(
            providers,
            session=scoped,
            recorder=recorder,
            observe=True,
            request_id=_resolve_request_id(request_id),
        )
        try:
            return gw.complete_json(
                task=task,
                messages=[Message(role="system", content=system), Message(role="user", content=user)],
                schema=schema,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # noqa: BLE001
            _log_llm_failure(task, exc)
            return None
