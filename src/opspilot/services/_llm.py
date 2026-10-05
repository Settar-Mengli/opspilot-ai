"""Shared helpers for LLM-backed services (X4 minimization)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from opspilot.llm.gateway import AttemptRecorder, session_attempt_recorder
from opspilot.llm.meta_redact import redact_text
from opspilot.llm.policy import llm_allowed
from opspilot.llm.prompt_safety import neutralize_text, wrap_untrusted
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
# Work item PKs are String(64); wi_{uuid4.hex} is 35 chars — never truncate below that.
_WORK_ITEM_ID_MAX = 64


def format_work_item_id_for_prompt(raw: object) -> str:
    """Neutralize a work-item id for prompts without chopping the PK."""
    return neutralize_text(str(raw if raw is not None else "?"))[:_WORK_ITEM_ID_MAX] or "?"


def compact_triage_lines(records: list[dict[str, Any]], *, include_title: bool = False) -> str:
    """X4-minimized triage context (fictional IDs / short reasons only), UNTRUSTED-wrapped."""
    if not records:
        return wrap_untrusted("queue", "queue: empty")
    lines = [f"queue: {min(len(records), _MAX_ITEMS)} items"]
    for record in records[:_MAX_ITEMS]:
        item_id = format_work_item_id_for_prompt(record.get("id", "?"))
        urgency = neutralize_text(str(record.get("urgency", "?")))[:16]
        category = neutralize_text(str(record.get("category", "?")))[:24]
        reason = neutralize_text(str(record.get("urgency_reason", "")))[:_MAX_REASON_CHARS]
        if include_title:
            title = neutralize_text(str(record.get("subject_or_title", "")))[:60]
            lines.append(f"{item_id}|{urgency}|{category}|{title}|{reason}")
        else:
            lines.append(f"{item_id}|{urgency}|{category}|{reason}")
    return wrap_untrusted("queue", "\n".join(lines))


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


def complete_structured_raising[T: BaseModel](
    *,
    task: TaskName,
    system: str,
    user: str,
    schema: type[T],
    max_tokens: int,
    session: Session,
    recorder: AttemptRecorder | None = None,
    request_id: str | None = None,
) -> T | None:
    """Like ``complete_structured`` but re-raises budget/exhaustion errors.

    * ``LlmProvidersExhausted`` and ``LlmPolicyDenied`` propagate to the caller
      so drain can distinguish budget-denied from soft failures.
    * All other exceptions are logged and return ``None`` (same as the soft variant).
    """
    from opspilot.llm.errors import LlmPolicyDenied, LlmProvidersExhausted

    if not llm_allowed():
        raise LlmPolicyDenied("remote LLM disabled by policy")
    providers = providers_or_empty()
    if not providers:
        raise LlmProvidersExhausted("no_providers")

    rec = recorder or session_attempt_recorder(session)
    gw = BudgetAwareGateway(
        providers,
        session=session,
        recorder=rec,
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
    except (LlmProvidersExhausted, LlmPolicyDenied):
        raise
    except Exception as exc:  # noqa: BLE001
        _log_llm_failure(task, exc)
        return None
