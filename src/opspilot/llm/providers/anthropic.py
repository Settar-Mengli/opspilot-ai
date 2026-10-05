"""Anthropic provider gated by D-023 (operator prepaid opt-in)."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from opspilot.llm.operator_auth import OperatorAnthropicAuth
from opspilot.llm.types import AttemptStatus, Message, ProviderResult, StreamChunk, TaskName
from opspilot.persistence.repositories.anthropic_budget import (
    ANTHROPIC_EST_INPUT_CAP,
    estimate_input_tokens,
    get_budget,
    reconcile_reservation,
    reserve_and_open_call,
)

_ALLOWLIST: frozenset[str] = frozenset({"ask", "triage"})
_MODEL_ALLOWLIST: frozenset[str] = frozenset({"claude-haiku-4-5-20251001"})
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def anthropic_enabled() -> bool:
    return os.environ.get("OPSPILOT_ANTHROPIC_ENABLED", "").strip().lower() in _TRUTHY


def _demo_mode_enabled() -> bool:
    return os.environ.get("OPSPILOT_DEMO_MODE", "0").strip().lower() in _TRUTHY


def _parse_decimal(name: str) -> Decimal | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        return Decimal(raw.strip())
    except Exception:  # noqa: BLE001
        return None


def usd_rates() -> tuple[Decimal, Decimal] | None:
    """Return (in_per_mtok, out_per_mtok) or None if either missing/invalid/non-positive."""
    inn = _parse_decimal("OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN")
    out = _parse_decimal("OPSPILOT_ANTHROPIC_USD_PER_MTOK_OUT")
    if inn is None or out is None or inn <= 0 or out <= 0:
        return None
    return inn, out


def task_allowlisted(task: TaskName) -> bool:
    return task in _ALLOWLIST


def anthropic_timeout_s() -> float:
    raw = os.environ.get("OPSPILOT_ANTHROPIC_TIMEOUT_S", "25").strip()
    try:
        val = float(raw)
    except ValueError:
        return 25.0
    return val if val > 0 else 25.0


def estimate_usd(*, input_tokens: int, output_tokens: int) -> Decimal | None:
    rates = usd_rates()
    if rates is None:
        return None
    inn, out = rates
    return (Decimal(input_tokens) * inn + Decimal(output_tokens) * out) / Decimal(1_000_000)


def gate_reason(
    task: TaskName,
    *,
    operator_auth: OperatorAnthropicAuth | None = None,
    session: Session | None = None,
    est_input: int | None = None,
    model: str | None = None,
) -> str | None:
    """Return a deny reason, or None if Anthropic may proceed to client+reserve.

    Soft-skip order (A3). Does not reserve; ledger existence checked when session given.
    """
    if operator_auth is None or operator_auth.role != "demo_operator":
        return "operator_auth_required"
    if not anthropic_enabled():
        return "anthropic_disabled"
    if _demo_mode_enabled():
        return "demo_mode"
    if not task_allowlisted(task):
        return "task_not_allowlisted"
    resolved = (model or os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")).strip()
    if resolved not in _MODEL_ALLOWLIST:
        return "model_not_allowlisted"
    if usd_rates() is None:
        return "missing_usd_rates"
    if est_input is not None and est_input > ANTHROPIC_EST_INPUT_CAP:
        return "est_input_over_cap"
    if session is not None:
        row = get_budget(session)
        if row is None:
            return "ledger_missing"
        if row.remaining_tokens <= 0 or row.remaining_usd <= 0:
            return "budget_exhausted"
    return None


def _classify_attempt_outcome(exc: BaseException) -> tuple[AttemptStatus, str, str]:
    """Classify ledger_op for an exception after reservation.

    SDK 1.8.0 map (site-packages/anthropic/_exceptions.py):
    - APIStatusError L71–92 + subclasses with status_code 4xx → refund
      (BadRequestError L135, AuthenticationError L139, PermissionDeniedError L143,
      NotFoundError L147, ConflictError L151, RequestTooLargeError L155,
      UnprocessableEntityError L159, RateLimitError L163)
    - APIStatusError 5xx → keep (ServiceUnavailableError L167, OverloadedError L171,
      DeadlineExceededError L175, InternalServerError L179)
    - APIConnectionError L95–97 (not timeout) → refund (connection refused / DNS /
      connect failure — request not proven sent)
    - APITimeoutError L100–105 → keep (connect vs read timeout not distinguishable)
    - CredentialsError L117–119 → refund (client credentials load, pre-send)
    - TypeError / ValueError → refund (client build / serialization, pre-send)
    - Anything else → keep (fail closed)
    """
    try:
        import anthropic
    except ImportError:  # pragma: no cover
        anthropic = None  # type: ignore[assignment]

    name = type(exc).__name__

    # Pre-send: serialization / client build failures
    if isinstance(exc, (TypeError, ValueError)):
        return AttemptStatus.ERROR, name, "refund"

    if anthropic is not None:
        # Credentials cannot be loaded — never reached the wire
        if isinstance(exc, getattr(anthropic, "CredentialsError", ())):
            return AttemptStatus.ERROR, name, "refund"
        # Timeout: ambiguous connect vs read → keep (cannot classify with certainty)
        if isinstance(exc, getattr(anthropic, "APITimeoutError", ())):
            return AttemptStatus.TIMEOUT, name, "keep"
        # Connection refused / DNS / connect failure — provably not sent
        if isinstance(exc, getattr(anthropic, "APIConnectionError", ())):
            return AttemptStatus.ERROR, name, "refund"
        # HTTP status errors
        if isinstance(exc, getattr(anthropic, "APIStatusError", ())):
            status_code = getattr(exc, "status_code", None)
            if isinstance(status_code, int):
                if 400 <= status_code < 500:
                    status = AttemptStatus.RATE_LIMITED if status_code == 429 else AttemptStatus.ERROR
                    return status, f"http_{status_code}", "refund"
                if status_code >= 500:
                    return AttemptStatus.ERROR, f"http_{status_code}", "keep"
            return AttemptStatus.ERROR, name, "keep"

    # Fallback for duck-typed / fake clients in hermetic tests (no SDK instance)
    status_code = getattr(exc, "status_code", None)
    if status_code is None:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        if 400 <= status_code < 500:
            status = AttemptStatus.RATE_LIMITED if status_code == 429 else AttemptStatus.ERROR
            return status, f"http_{status_code}", "refund"
        if status_code >= 500:
            return AttemptStatus.ERROR, f"http_{status_code}", "keep"
    lower = name.lower()
    if "timeout" in lower or "timedout" in lower or "api_timeout" in lower:
        return AttemptStatus.TIMEOUT, name, "keep"
    if "apiconnectionerror" in lower or "connectionerror" in lower:
        return AttemptStatus.ERROR, name, "refund"
    return AttemptStatus.ERROR, name, "keep"


class AnthropicProvider:
    """Anthropic Messages API behind D-023 operator gate. Never construct client when gated off."""

    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: Any | None = None,
        operator_auth: OperatorAnthropicAuth | None = None,
        session: Session | None = None,
    ) -> None:
        self._api_key = (api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")).strip()
        self._client = client
        self._model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001").strip()
        self.operator_auth = operator_auth
        self.session = session
        self.anthropic_attempts: int = 0
        self._last_create_kwargs: dict[str, Any] | None = None

    def _est_input(self, messages: list[Message]) -> int:
        return estimate_input_tokens(*(m.content for m in messages))

    def _ensure_client(
        self, task: TaskName, *, est_input: int | None = None, model: str | None = None
    ) -> tuple[Any | None, str | None]:
        reason = gate_reason(
            task,
            operator_auth=self.operator_auth,
            session=self.session,
            est_input=est_input,
            model=model or self._model,
        )
        if reason is not None:
            return None, reason
        if self._client is not None:
            return self._client, None
        if not self._api_key:
            return None, "missing_api_key"
        import anthropic

        self._client = anthropic.Anthropic(
            api_key=self._api_key,
            max_retries=0,
            timeout=anthropic_timeout_s(),
        )
        return self._client, None

    def _reconcile(
        self,
        *,
        call_id: int,
        ledger_op: str,
        final_status: AttemptStatus,
        actual_tokens: int = 0,
        actual_usd: Decimal | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        error_code: str | None = None,
        extra_meta: dict[str, Any] | None = None,
    ) -> None:
        if self.session is None:
            return
        reconcile_reservation(
            self.session,
            call_id=call_id,
            final_status=final_status.value,
            ledger_op=ledger_op,
            actual_tokens=actual_tokens,
            actual_usd=actual_usd,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            error_code=error_code,
            extra_meta=extra_meta,
        )

    def complete(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int,
        model: str | None = None,
    ) -> ProviderResult:
        resolved = model or self._model
        est_input = self._est_input(messages)
        client, reason = self._ensure_client(task, est_input=est_input, model=resolved)
        if client is None:
            status = AttemptStatus.POLICY_DENIED
            if reason in {"budget_exhausted", "ledger_missing"}:
                status = AttemptStatus.BUDGET_DENIED
            if reason == "missing_api_key":
                status = AttemptStatus.ERROR
            return ProviderResult(status=status, model=resolved, error_code=reason)

        rates = usd_rates()
        assert rates is not None  # gated
        inn, out = rates
        reserve_tokens = est_input + max_tokens
        reserve_usd = (Decimal(est_input) * inn + Decimal(max_tokens) * out) / Decimal(1_000_000)

        call_id: int | None = None
        if self.session is not None:
            open_row = reserve_and_open_call(
                self.session,
                tokens=reserve_tokens,
                usd=reserve_usd,
                task=task,
                model=resolved,
            )
            if open_row is None:
                return ProviderResult(
                    status=AttemptStatus.BUDGET_DENIED,
                    model=resolved,
                    error_code="reservation_failed",
                )
            call_id = open_row.id
            self.session.flush()

        self.anthropic_attempts += 1
        system = "\n".join(m.content for m in messages if m.role == "system")
        user_msgs = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        create_kwargs = {
            "model": resolved,
            "max_tokens": max_tokens,
            "system": system or "You are a helpful assistant.",
            "messages": user_msgs or [{"role": "user", "content": ""}],
        }
        self._last_create_kwargs = dict(create_kwargs)
        started = time.perf_counter()
        try:
            resp = client.messages.create(**create_kwargs)
        except Exception as exc:  # noqa: BLE001
            latency = int((time.perf_counter() - started) * 1000)
            # Pre-send style failures (client never got a response object): treat unknown
            # construction failures already handled; transport after create → classify.
            status, err, ledger_op = _classify_attempt_outcome(exc)
            if call_id is not None:
                self._reconcile(
                    call_id=call_id,
                    ledger_op=ledger_op,
                    final_status=status,
                    error_code=err,
                )
            return ProviderResult(
                status=status,
                model=resolved,
                error_code=err,
                latency_ms=latency,
                meta={"ledger_row_owned": True} if call_id is not None else {},
            )

        text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        usage = getattr(resp, "usage", None)
        tin = int(getattr(usage, "input_tokens", 0) or 0)
        tout = int(getattr(usage, "output_tokens", 0) or 0)
        actual_tokens = tin + tout
        actual_usd = estimate_usd(input_tokens=tin, output_tokens=tout) or Decimal(0)
        if call_id is not None:
            if actual_tokens <= reserve_tokens and actual_usd <= reserve_usd:
                self._reconcile(
                    call_id=call_id,
                    ledger_op="refund_delta",
                    final_status=AttemptStatus.SUCCESS,
                    actual_tokens=actual_tokens,
                    actual_usd=actual_usd,
                    tokens_in=tin,
                    tokens_out=tout,
                    error_code=None,
                )
            else:
                self._reconcile(
                    call_id=call_id,
                    ledger_op="excess",
                    final_status=AttemptStatus.SUCCESS,
                    actual_tokens=actual_tokens,
                    actual_usd=actual_usd,
                    tokens_in=tin,
                    tokens_out=tout,
                    error_code=None,
                )
        return ProviderResult(
            status=AttemptStatus.SUCCESS,
            text="".join(text_parts),
            model=resolved,
            input_tokens=tin,
            output_tokens=tout,
            latency_ms=int((time.perf_counter() - started) * 1000),
            raw={"usd_estimate": str(actual_usd)},
            meta={"ledger_row_owned": True} if call_id is not None else {},
        )

    def complete_json(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        schema: type[BaseModel],
        max_tokens: int,
        model: str | None = None,
        repair_hint: str | None = None,
        force_json_object: bool = False,
        temperature: float | None = None,
    ) -> ProviderResult:
        del schema, force_json_object, temperature  # prompt-only JSON for Anthropic
        msgs = list(messages)
        if repair_hint:
            msgs.append(Message(role="user", content=f"Fix JSON. Errors: {repair_hint}"))
        msgs.append(Message(role="user", content="Respond with JSON only."))
        return self.complete(task=task, messages=msgs, max_tokens=max_tokens, model=model)

    def stream(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int,
        model: str | None = None,
    ) -> Iterator[StreamChunk]:
        result = self.complete(task=task, messages=messages, max_tokens=max_tokens, model=model)
        yield StreamChunk(text=result.text, provider=self.name, model=result.model, done=True)
