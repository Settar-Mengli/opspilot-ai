"""Hand-rolled LLM gateway (D-012)."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence

from pydantic import BaseModel, ValidationError

from opspilot.llm.errors import LlmPolicyDenied, LlmProvidersExhausted, LlmSchemaError
from opspilot.llm.policy import llm_allowed
from opspilot.llm.providers.base import LlmProvider
from opspilot.llm.types import AttemptStatus, CompletionResult, Message, StreamChunk, TaskName

_REPAIR_SUFFIX = (
    "Your previous JSON failed validation. Return corrected JSON only that matches the schema. "
    "Validation errors:\n{errors}"
)


class LlmGateway:
    """Thin multi-provider gateway: complete / complete_json / stream.

    C2 skeleton: inject providers explicitly (typically FakeProvider in tests).
    Routing, budgets, and LlmCall persistence land in later commits.
    """

    def __init__(self, providers: Sequence[LlmProvider]) -> None:
        if not providers:
            raise ValueError("LlmGateway requires at least one provider")
        self._providers = list(providers)

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
                return
            except Exception as exc:  # noqa: BLE001 — failover to next provider
                last_error = str(exc)
                continue
        raise LlmProvidersExhausted(last_error or "all providers failed to stream")

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


def complete(
    *,
    task: TaskName,
    messages: list[Message],
    providers: Sequence[LlmProvider],
    max_tokens: int = 1024,
    model: str | None = None,
) -> CompletionResult:
    """Module-level helper for callers that build a one-shot gateway."""
    return LlmGateway(providers).complete(task=task, messages=messages, max_tokens=max_tokens, model=model)


def complete_json[T: BaseModel](
    *,
    task: TaskName,
    messages: list[Message],
    schema: type[T],
    providers: Sequence[LlmProvider],
    max_tokens: int = 1024,
    model: str | None = None,
) -> T:
    return LlmGateway(providers).complete_json(
        task=task, messages=messages, schema=schema, max_tokens=max_tokens, model=model
    )


def stream(
    *,
    task: TaskName,
    messages: list[Message],
    providers: Sequence[LlmProvider],
    max_tokens: int = 1024,
    model: str | None = None,
) -> Iterator[StreamChunk]:
    return LlmGateway(providers).stream(task=task, messages=messages, max_tokens=max_tokens, model=model)
