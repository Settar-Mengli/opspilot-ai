"""Budget- and circuit-aware completion helper."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import replace

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from opspilot.llm.budgets import add_tokens, tokens_exhausted, try_consume_request
from opspilot.llm.circuit import CircuitBreaker
from opspilot.llm.errors import LlmPolicyDenied, LlmProvidersExhausted, LlmSchemaError
from opspilot.llm.gateway import AttemptRecorder, default_observe_attempt
from opspilot.llm.json_extract import extract_json_object
from opspilot.llm.meta_redact import parse_failure_meta
from opspilot.llm.policy import llm_allowed
from opspilot.llm.prompts.versioning import prompt_version_sha256
from opspilot.llm.providers.base import LlmProvider
from opspilot.llm.routing import filter_by_circuit
from opspilot.llm.schema_convert import schema_prompt_fragment, unwrap_schema_echo
from opspilot.llm.types import AttemptStatus, CompletionResult, Message, ProviderResult, TaskName

_REPAIR_SUFFIX = (
    "Your previous JSON failed validation. Return corrected JSON only that matches the schema. "
    "Validation errors:\n{errors}\n{schema_frag}"
)

# Provider 400 bodies that indicate schema / response_format rejection (S2 fixtures).
_SCHEMA_FORMAT_HINTS = (
    "$defs",
    "$ref",
    "additionalproperties",
    "responseschema",
    "json_schema",
    "response_format",
    "invalid_argument",
    "unknown name",
    "strict mode",
    "failed_generation",
)


def is_schema_format_http_error(result: ProviderResult) -> bool:
    """True when a non-2xx looks like schema/format rejection (retry as json_object)."""
    if result.error_code not in {"http_400", "http_422"}:
        return False
    err = str((result.meta or {}).get("provider_error") or "").lower()
    return any(h in err for h in _SCHEMA_FORMAT_HINTS)


class BudgetAwareGateway:
    """Try providers in order with per-attempt budget debit + circuit.

    A missing Session is fail-closed (budget_denied); never skip budget checks.
    """

    def __init__(
        self,
        providers: Sequence[LlmProvider],
        *,
        session: Session | None = None,
        circuit: CircuitBreaker | None = None,
        recorder: AttemptRecorder | None = None,
        observe: bool = True,
        request_id: str | None = None,
        honor_retry_after: bool = True,
        request_pacer: Callable[[], None] | None = None,
    ) -> None:
        self._providers = list(providers)
        self._session = session
        self._circuit = circuit or CircuitBreaker()
        self._recorder = recorder
        self._observe = observe
        self._request_id = request_id
        self._honor_retry_after = honor_retry_after
        self._request_pacer = request_pacer
        self.last_repair_used: bool = False
        self.last_parse_error_class: str | None = None
        self.last_parse_output_head: str | None = None
        self.last_provider: str | None = None
        self.last_model: str | None = None
        self.last_success_text: str | None = None

    def complete(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int = 1024,
        model: str | None = None,
    ) -> CompletionResult:
        if not llm_allowed():
            raise LlmPolicyDenied("remote LLM disabled by policy")
        if self._session is None:
            self._deny_no_session(task=task, model=model)
            raise LlmProvidersExhausted("budget_denied_no_session")

        prompt_version = prompt_version_sha256(task=task, messages=messages)
        candidates = filter_by_circuit(self._providers, self._circuit)
        last_error: str | None = None
        for provider in candidates:
            if not self._try_budget(task=task, provider=provider.name, model=model, prompt_version=prompt_version):
                last_error = "budget_denied"
                continue

            attempt = provider.complete(task=task, messages=messages, max_tokens=max_tokens, model=model)
            self._record(task=task, provider=provider.name, result=attempt, prompt_version=prompt_version)

            if attempt.status is AttemptStatus.SUCCESS:
                add_tokens(
                    self._session,
                    provider=provider.name,
                    tokens=attempt.input_tokens + attempt.output_tokens,
                )
                self._circuit.reset(provider.name)
                return CompletionResult(
                    text=attempt.text,
                    provider=provider.name,
                    model=attempt.model,
                    input_tokens=attempt.input_tokens,
                    output_tokens=attempt.output_tokens,
                    latency_ms=attempt.latency_ms,
                    raw=attempt.raw,
                )

            if attempt.status in {AttemptStatus.TIMEOUT, AttemptStatus.ERROR, AttemptStatus.RATE_LIMITED}:
                self._circuit.trip(provider.name)
            if (
                attempt.status is AttemptStatus.RATE_LIMITED
                and self._honor_retry_after
                and attempt.retry_after_s
                and 0 < attempt.retry_after_s <= 2.0
            ):
                time.sleep(attempt.retry_after_s)
            last_error = attempt.error_code or attempt.status.value

        raise LlmProvidersExhausted(last_error or "all providers failed or budget-denied")

    def complete_json[T: BaseModel](
        self,
        *,
        task: TaskName,
        messages: list[Message],
        schema: type[T],
        max_tokens: int = 1024,
        model: str | None = None,
        exclude_providers: frozenset[str] | set[str] | None = None,
        prefer_provider: str | None = None,
    ) -> T:
        """Structured complete with one repair; each provider/repair attempt debits budget."""
        if not llm_allowed():
            raise LlmPolicyDenied("remote LLM disabled by policy")
        if self._session is None:
            self._deny_no_session(task=task, model=model)
            raise LlmProvidersExhausted("budget_denied_no_session")

        self.last_repair_used = False
        self.last_parse_error_class = None
        self.last_parse_output_head = None
        self.last_success_text = None

        prompt_version = prompt_version_sha256(task=task, messages=messages)
        exclude = frozenset(exclude_providers or ())
        candidates = [p for p in filter_by_circuit(self._providers, self._circuit) if p.name not in exclude]
        prefer = (prefer_provider or "").strip()
        if prefer:
            preferred = [p for p in candidates if p.name == prefer]
            rest = [p for p in candidates if p.name != prefer]
            candidates = preferred + rest
        if not candidates:
            raise LlmProvidersExhausted("circuit_open" if not exclude else "providers_excluded")
        last_error: str | None = None
        for provider in candidates:
            attempt, used_force_json = self._structured_attempt(
                provider=provider,
                task=task,
                messages=messages,
                schema=schema,
                max_tokens=max_tokens,
                model=model,
                prompt_version=prompt_version,
                force_json_object=False,
            )
            if attempt is None:
                last_error = "budget_denied"
                continue
            if attempt.status is not AttemptStatus.SUCCESS:
                if not used_force_json and is_schema_format_http_error(attempt):
                    retry, _ = self._structured_attempt(
                        provider=provider,
                        task=task,
                        messages=messages,
                        schema=schema,
                        max_tokens=max_tokens,
                        model=model,
                        prompt_version=prompt_version,
                        force_json_object=True,
                    )
                    if retry is None:
                        last_error = "budget_denied"
                        continue
                    attempt = retry
                    used_force_json = True
                    if attempt.status is not AttemptStatus.SUCCESS:
                        if attempt.status in {
                            AttemptStatus.TIMEOUT,
                            AttemptStatus.ERROR,
                            AttemptStatus.RATE_LIMITED,
                        }:
                            self._circuit.trip(provider.name)
                        last_error = attempt.error_code or attempt.status.value
                        continue
                else:
                    if attempt.status in {
                        AttemptStatus.TIMEOUT,
                        AttemptStatus.ERROR,
                        AttemptStatus.RATE_LIMITED,
                    }:
                        self._circuit.trip(provider.name)
                    last_error = attempt.error_code or attempt.status.value
                    continue

            add_tokens(
                self._session,
                provider=provider.name,
                tokens=attempt.input_tokens + attempt.output_tokens,
            )
            parsed, errors, error_class = self._try_parse(schema, attempt.text)
            if parsed is not None:
                self.last_provider = provider.name
                self.last_model = attempt.model or "unknown"
                self.last_success_text = attempt.text
                self._record(task=task, provider=provider.name, result=attempt, prompt_version=prompt_version)
                self._circuit.reset(provider.name)
                return parsed

            self.last_parse_error_class = error_class
            self.last_parse_output_head = (attempt.text or "")[:300]
            failed = replace(
                attempt,
                meta={
                    **dict(attempt.meta),
                    **parse_failure_meta(
                        error_class=error_class,
                        validation_error=errors,
                        raw_output=attempt.text,
                    ),
                },
            )
            self._record(task=task, provider=provider.name, result=failed, prompt_version=prompt_version)

            schema_frag = schema_prompt_fragment(schema)
            repair_messages = [
                *messages,
                Message(role="assistant", content=attempt.text),
                Message(
                    role="user",
                    content=_REPAIR_SUFFIX.format(errors=errors, schema_frag=schema_frag),
                ),
            ]
            repair_pv = prompt_version_sha256(task=task, messages=repair_messages)
            repair, _ = self._structured_attempt(
                provider=provider,
                task=task,
                messages=repair_messages,
                schema=schema,
                max_tokens=max_tokens,
                model=model,
                prompt_version=repair_pv,
                force_json_object=used_force_json,
                repair_hint=errors,
            )
            if repair is None:
                last_error = "budget_denied_repair"
                continue
            if repair.status is not AttemptStatus.SUCCESS:
                if repair.status in {AttemptStatus.TIMEOUT, AttemptStatus.ERROR, AttemptStatus.RATE_LIMITED}:
                    self._circuit.trip(provider.name)
                last_error = repair.error_code or repair.status.value
                continue

            add_tokens(
                self._session,
                provider=provider.name,
                tokens=repair.input_tokens + repair.output_tokens,
            )
            parsed_repair, repair_errors, repair_class = self._try_parse(schema, repair.text)
            if parsed_repair is not None:
                self.last_repair_used = True
                self.last_provider = provider.name
                self.last_model = repair.model or "unknown"
                self.last_success_text = repair.text
                self._record(task=task, provider=provider.name, result=repair, prompt_version=repair_pv)
                self._circuit.reset(provider.name)
                return parsed_repair
            self.last_parse_error_class = repair_class
            self.last_parse_output_head = (repair.text or "")[:300]
            repair_failed = replace(
                repair,
                meta={
                    **dict(repair.meta),
                    **parse_failure_meta(
                        error_class=repair_class,
                        validation_error=repair_errors,
                        raw_output=repair.text,
                    ),
                },
            )
            self._record(task=task, provider=provider.name, result=repair_failed, prompt_version=repair_pv)
            last_error = repair_errors

        # Schema path only when the last failure was parse/validation; else provider/budget exhaustion.
        if last_error in {"budget_denied", "budget_denied_repair", "429"} or (
            last_error
            and (
                last_error.startswith("http_")
                or last_error
                in {
                    "timeout",
                    "rate_limited",
                    "circuit_open",
                    "all providers failed or budget-denied",
                }
            )
        ):
            raise LlmProvidersExhausted(last_error)
        raise LlmSchemaError(last_error or "schema validation failed")

    def _structured_attempt(
        self,
        *,
        provider: LlmProvider,
        task: TaskName,
        messages: list[Message],
        schema: type[BaseModel],
        max_tokens: int,
        model: str | None,
        prompt_version: str | None,
        force_json_object: bool,
        repair_hint: str | None = None,
    ) -> tuple[ProviderResult | None, bool]:
        """Budget-debit + one provider complete_json; records HTTP failures immediately."""
        if not self._try_budget(
            task=task,
            provider=provider.name,
            model=model,
            prompt_version=prompt_version,
        ):
            return None, force_json_object
        if self._request_pacer is not None:
            self._request_pacer()
        attempt = provider.complete_json(
            task=task,
            messages=messages,
            schema=schema,
            max_tokens=max_tokens,
            model=model,
            repair_hint=repair_hint,
            force_json_object=force_json_object,
            temperature=0.0,
        )
        if force_json_object and attempt.meta is not None:
            attempt = replace(attempt, meta={**dict(attempt.meta), "force_json_object": True})
        elif force_json_object:
            attempt = replace(attempt, meta={"force_json_object": True})
        if attempt.status is not AttemptStatus.SUCCESS:
            self._record(task=task, provider=provider.name, result=attempt, prompt_version=prompt_version)
        return attempt, force_json_object

    def _try_budget(
        self,
        *,
        task: TaskName,
        provider: str,
        model: str | None,
        prompt_version: str | None = None,
    ) -> bool:
        assert self._session is not None
        if tokens_exhausted(self._session, provider=provider):
            self._record(
                task=task,
                provider=provider,
                result=ProviderResult(status=AttemptStatus.BUDGET_DENIED, model=model or "", error_code="tok_cap"),
                prompt_version=prompt_version,
            )
            return False
        if not try_consume_request(self._session, provider=provider):
            self._record(
                task=task,
                provider=provider,
                result=ProviderResult(status=AttemptStatus.BUDGET_DENIED, model=model or "", error_code="req_cap"),
                prompt_version=prompt_version,
            )
            return False
        return True

    def _deny_no_session(self, *, task: TaskName, model: str | None) -> None:
        name = self._providers[0].name if self._providers else "none"
        self._record(
            task=task,
            provider=name,
            result=ProviderResult(status=AttemptStatus.BUDGET_DENIED, model=model or "", error_code="no_session"),
            prompt_version=None,
        )

    @staticmethod
    def _try_parse[T: BaseModel](schema: type[T], text: str) -> tuple[T | None, str, str]:
        extracted = extract_json_object(text)
        try:
            data = json.loads(extracted)
        except json.JSONDecodeError as exc:
            return None, f"invalid JSON: {exc}", "json_decode"
        data = unwrap_schema_echo(data)
        try:
            return schema.model_validate(data), "", "ok"
        except ValidationError as exc:
            return None, str(exc), "schema_validation"

    def _record(
        self,
        *,
        task: TaskName,
        provider: str,
        result: ProviderResult,
        prompt_version: str | None = None,
    ) -> None:
        if self._observe:
            default_observe_attempt(
                task=task,
                provider=provider,
                result=result,
                request_id=self._request_id,
                prompt_version=prompt_version,
            )
        if self._recorder is not None:
            self._recorder(
                task=task,
                provider=provider,
                result=result,
                request_id=self._request_id,
                prompt_version=prompt_version,
            )
