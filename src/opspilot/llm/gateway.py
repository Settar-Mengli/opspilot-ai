"""Hand-rolled LLM gateway (D-012)."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from typing import Protocol

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from opspilot.llm.errors import LlmPolicyDenied, LlmProvidersExhausted, LlmSchemaError
from opspilot.llm.policy import llm_allowed
from opspilot.llm.providers.base import LlmProvider
from opspilot.llm.types import AttemptStatus, CompletionResult, Message, ProviderResult, StreamChunk, TaskName
from opspilot.obs.tracing import LlmSpanAttrs, append_llm_jsonl, emit_llm_span
from opspilot.persistence.llm_calls import record_llm_call

_REPAIR_SUFFIX = (
    "Your previous JSON failed validation. Return corrected JSON only that matches the schema. "
    "Validation errors:\n{errors}"
)


class AttemptRecorder(Protocol):
    """Persists one provider attempt (typically to llm_calls)."""

    def __call__(
        self,
        *,
        task: TaskName,
        provider: str,
        result: ProviderResult,
        request_id: str | None = None,
    ) -> None: ...


def default_observe_attempt(
    *,
    task: TaskName,
    provider: str,
    result: ProviderResult,
    request_id: str | None = None,
) -> None:
    """JSONL + structured span for an attempt (no DB)."""
    attrs = LlmSpanAttrs(
        task=task,
        provider=provider,
        model=result.model or "unknown",
        status=result.status.value,
        latency_ms=result.latency_ms,
        tokens_in=result.input_tokens,
        tokens_out=result.output_tokens,
        request_id=request_id,
        error_code=result.error_code,
    )
    emit_llm_span(attrs)
    append_llm_jsonl(attrs)


class LlmGateway:
    """Thin multi-provider gateway: complete / complete_json / stream.

    C2 skeleton: inject providers explicitly (typically FakeProvider in tests).
    Routing and budgets land in later commits; attempt metering hooks are optional.
    """

    def __init__(
        self,
        providers: Sequence[LlmProvider],
        *,
        recorder: AttemptRecorder | None = None,
        observe: bool = True,
        request_id: str | None = None,
    ) -> None:
        if not providers:
            raise ValueError("LlmGateway requires at least one provider")
        self._providers = list(providers)
        self._recorder = recorder
        self._observe = observe
        self._request_id = request_id

    def complete(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int = 1024,
        model: str | None = None,
        require_remote: bool = True,
    ) -> CompletionResult:
        self._assert_policy(require_remote=require_remote)
        last_error: str | None = None
        for provider in self._providers:
            result = provider.complete(task=task, messages=messages, max_tokens=max_tokens, model=model)
            self._record(task=task, provider=provider.name, result=result)
            if result.status is AttemptStatus.SUCCESS:
                return CompletionResult(
                    text=result.text,
                    provider=provider.name,
                    model=result.model,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    latency_ms=result.latency_ms,
                    raw=result.raw,
                )
            last_error = result.error_code or result.status.value
        raise LlmProvidersExhausted(last_error or "all providers failed")

    def complete_json[T: BaseModel](
        self,
        *,
        task: TaskName,
        messages: list[Message],
        schema: type[T],
        max_tokens: int = 1024,
        model: str | None = None,
        require_remote: bool = True,
    ) -> T:
        self._assert_policy(require_remote=require_remote)
        last_error: str | None = None
        for provider in self._providers:
            attempt = provider.complete_json(
                task=task,
                messages=messages,
                schema=schema,
                max_tokens=max_tokens,
                model=model,
            )
            self._record(task=task, provider=provider.name, result=attempt)
            if attempt.status is not AttemptStatus.SUCCESS:
                last_error = attempt.error_code or attempt.status.value
                continue
            parsed, errors = self._try_parse(schema, attempt.text)
            if parsed is not None:
                return parsed
            # One repair retry (D-013).
            repair_messages = [
                *messages,
                Message(role="assistant", content=attempt.text),
                Message(role="user", content=_REPAIR_SUFFIX.format(errors=errors)),
            ]
            repair = provider.complete_json(
                task=task,
                messages=repair_messages,
                schema=schema,
                max_tokens=max_tokens,
                model=model,
                repair_hint=errors,
            )
            self._record(task=task, provider=provider.name, result=repair)
            if repair.status is not AttemptStatus.SUCCESS:
                last_error = repair.error_code or repair.status.value
                continue
            parsed_repair, repair_errors = self._try_parse(schema, repair.text)
            if parsed_repair is not None:
                return parsed_repair
            last_error = repair_errors
        raise LlmSchemaError(last_error or "schema validation failed")

    def stream(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int = 1024,
        model: str | None = None,
        require_remote: bool = True,
    ) -> Iterator[StreamChunk]:
        self._assert_policy(require_remote=require_remote)
        last_error: str | None = None
        for provider in self._providers:
            try:
                yield from provider.stream(task=task, messages=messages, max_tokens=max_tokens, model=model)
                self._record(
                    task=task,
                    provider=provider.name,
                    result=ProviderResult(status=AttemptStatus.SUCCESS, model=model or "", text=""),
                )
                return
            except Exception as exc:  # noqa: BLE001 — failover to next provider
                last_error = str(exc)
                self._record(
                    task=task,
                    provider=provider.name,
                    result=ProviderResult(
                        status=AttemptStatus.ERROR,
                        model=model or "",
                        error_code=type(exc).__name__,
                    ),
                )
                continue
        raise LlmProvidersExhausted(last_error or "all providers failed to stream")

    def _record(self, *, task: TaskName, provider: str, result: ProviderResult) -> None:
        if self._observe:
            default_observe_attempt(task=task, provider=provider, result=result, request_id=self._request_id)
        if self._recorder is not None:
            self._recorder(task=task, provider=provider, result=result, request_id=self._request_id)

    @staticmethod
    def _assert_policy(*, require_remote: bool) -> None:
        if require_remote and not llm_allowed():
            raise LlmPolicyDenied("remote LLM disabled by policy")

    @staticmethod
    def _try_parse[T: BaseModel](schema: type[T], text: str) -> tuple[T | None, str]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            return None, f"invalid JSON: {exc}"
        try:
            return schema.model_validate(data), ""
        except ValidationError as exc:
            return None, str(exc)


def session_attempt_recorder(session: Session) -> AttemptRecorder:
    """Build a recorder that writes LlmCallRow via an open SQLAlchemy Session."""

    def _record(
        *,
        task: TaskName,
        provider: str,
        result: ProviderResult,
        request_id: str | None = None,
    ) -> None:
        record_llm_call(
            session,
            task=task,
            provider=provider,
            model=result.model or "unknown",
            status=result.status.value,
            latency_ms=result.latency_ms,
            tokens_in=result.input_tokens,
            tokens_out=result.output_tokens,
            request_id=request_id,
            error_code=result.error_code,
            meta={},
        )

    return _record


def complete(
    *,
    task: TaskName,
    messages: list[Message],
    providers: Sequence[LlmProvider],
    max_tokens: int = 1024,
    model: str | None = None,
    recorder: AttemptRecorder | None = None,
) -> CompletionResult:
    """Module-level helper for callers that build a one-shot gateway."""
    return LlmGateway(providers, recorder=recorder).complete(
        task=task, messages=messages, max_tokens=max_tokens, model=model
    )


def complete_json[T: BaseModel](
    *,
    task: TaskName,
    messages: list[Message],
    schema: type[T],
    providers: Sequence[LlmProvider],
    max_tokens: int = 1024,
    model: str | None = None,
    recorder: AttemptRecorder | None = None,
) -> T:
    return LlmGateway(providers, recorder=recorder).complete_json(
        task=task, messages=messages, schema=schema, max_tokens=max_tokens, model=model
    )


def stream(
    *,
    task: TaskName,
    messages: list[Message],
    providers: Sequence[LlmProvider],
    max_tokens: int = 1024,
    model: str | None = None,
    recorder: AttemptRecorder | None = None,
) -> Iterator[StreamChunk]:
    return LlmGateway(providers, recorder=recorder).stream(
        task=task, messages=messages, max_tokens=max_tokens, model=model
    )
