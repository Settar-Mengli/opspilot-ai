"""Anthropic provider gated by D-023 (prepaid opt-in only)."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from opspilot.llm.types import AttemptStatus, Message, ProviderResult, StreamChunk, TaskName

_ALLOWLIST: frozenset[str] = frozenset({"demo_quality", "leaderboard", "judge_calibration"})
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def anthropic_enabled() -> bool:
    return os.environ.get("OPSPILOT_ANTHROPIC_ENABLED", "").strip().lower() in _TRUTHY


def _parse_decimal(name: str) -> Decimal | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        return Decimal(raw.strip())
    except Exception:  # noqa: BLE001
        return None


def _parse_int(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def usd_rates() -> tuple[Decimal, Decimal] | None:
    """Return (in_per_mtok, out_per_mtok) or None if either missing/invalid."""
    inn = _parse_decimal("OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN")
    out = _parse_decimal("OPSPILOT_ANTHROPIC_USD_PER_MTOK_OUT")
    if inn is None or out is None:
        return None
    return inn, out


def remaining_token_budget() -> int | None:
    return _parse_int("OPSPILOT_ANTHROPIC_BUDGET_TOKENS")


def remaining_usd_budget() -> Decimal | None:
    return _parse_decimal("OPSPILOT_ANTHROPIC_BUDGET_USD")


def task_allowlisted(task: TaskName) -> bool:
    return task in _ALLOWLIST


def gate_reason(task: TaskName) -> str | None:
    """Return a deny reason, or None if Anthropic may be constructed for this task."""
    if not anthropic_enabled():
        return "anthropic_disabled"
    if not task_allowlisted(task):
        return "task_not_allowlisted"
    rates = usd_rates()
    if rates is None:
        return "missing_usd_rates"
    tok = remaining_token_budget()
    usd = remaining_usd_budget()
    if tok is None or tok <= 0:
        return "token_budget_exhausted"
    if usd is None or usd <= 0:
        return "usd_budget_exhausted"
    return None


def estimate_usd(*, input_tokens: int, output_tokens: int) -> Decimal | None:
    rates = usd_rates()
    if rates is None:
        return None
    inn, out = rates
    return (Decimal(input_tokens) * inn + Decimal(output_tokens) * out) / Decimal(1_000_000)


class AnthropicProvider:
    """Anthropic Messages API behind D-023 gate. Never construct client when gated off."""

    name = "anthropic"

    def __init__(self, *, api_key: str | None = None, client: Any | None = None) -> None:
        self._api_key = (api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")).strip()
        self._client = client
        self._model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001").strip()

    def _ensure_client(self, task: TaskName) -> tuple[Any | None, str | None]:
        reason = gate_reason(task)
        if reason is not None:
            return None, reason
        if self._client is not None:
            return self._client, None
        if not self._api_key:
            return None, "missing_api_key"
        import anthropic

        self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client, None

    def complete(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int,
        model: str | None = None,
    ) -> ProviderResult:
        client, reason = self._ensure_client(task)
        if client is None:
            status = AttemptStatus.POLICY_DENIED if reason != "missing_api_key" else AttemptStatus.ERROR
            if reason in {"token_budget_exhausted", "usd_budget_exhausted"}:
                status = AttemptStatus.BUDGET_DENIED
            return ProviderResult(status=status, model=model or self._model, error_code=reason)

        resolved = model or self._model
        system = "\n".join(m.content for m in messages if m.role == "system")
        user_msgs = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        started = time.perf_counter()
        try:
            resp = client.messages.create(
                model=resolved,
                max_tokens=max_tokens,
                system=system or "You are a helpful assistant.",
                messages=user_msgs or [{"role": "user", "content": ""}],
            )
        except Exception as exc:  # noqa: BLE001
            return ProviderResult(
                status=AttemptStatus.ERROR,
                model=resolved,
                error_code=type(exc).__name__,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        usage = getattr(resp, "usage", None)
        tin = int(getattr(usage, "input_tokens", 0) or 0)
        tout = int(getattr(usage, "output_tokens", 0) or 0)
        return ProviderResult(
            status=AttemptStatus.SUCCESS,
            text="".join(text_parts),
            model=resolved,
            input_tokens=tin,
            output_tokens=tout,
            latency_ms=int((time.perf_counter() - started) * 1000),
            raw={"usd_estimate": str(estimate_usd(input_tokens=tin, output_tokens=tout))},
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
        del schema, force_json_object, temperature  # prompt-only JSON for Anthropic in B2
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
