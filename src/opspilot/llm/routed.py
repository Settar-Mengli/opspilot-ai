"""Budget- and circuit-aware completion helper."""

from __future__ import annotations

import time
from collections.abc import Sequence

from sqlalchemy.orm import Session

from opspilot.llm.budgets import add_tokens, tokens_exhausted, try_consume_request
from opspilot.llm.circuit import CircuitBreaker
from opspilot.llm.errors import LlmPolicyDenied, LlmProvidersExhausted
from opspilot.llm.gateway import AttemptRecorder, default_observe_attempt
from opspilot.llm.policy import llm_allowed
from opspilot.llm.providers.base import LlmProvider
from opspilot.llm.routing import filter_by_circuit
from opspilot.llm.types import AttemptStatus, CompletionResult, Message, ProviderResult, TaskName


class BudgetAwareGateway:
    """Try providers in order with per-attempt budget debit + circuit."""

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
    ) -> None:
        self._providers = list(providers)
        self._session = session
        self._circuit = circuit or CircuitBreaker()
        self._recorder = recorder
        self._observe = observe
        self._request_id = request_id
        self._honor_retry_after = honor_retry_after

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

        candidates = filter_by_circuit(self._providers, self._circuit)
        last_error: str | None = None
        for provider in candidates:
            if self._session is not None:
                if tokens_exhausted(self._session, provider=provider.name):
                    self._record(
                        task=task,
                        provider=provider.name,
                        result=ProviderResult(
                            status=AttemptStatus.BUDGET_DENIED, model=model or "", error_code="tok_cap"
                        ),
                    )
                    last_error = "budget_denied_tokens"
                    continue
                if not try_consume_request(self._session, provider=provider.name):
                    self._record(
                        task=task,
                        provider=provider.name,
                        result=ProviderResult(
                            status=AttemptStatus.BUDGET_DENIED, model=model or "", error_code="req_cap"
                        ),
                    )
                    last_error = "budget_denied_req"
                    continue

            attempt = provider.complete(task=task, messages=messages, max_tokens=max_tokens, model=model)
            self._record(task=task, provider=provider.name, result=attempt)

            if attempt.status is AttemptStatus.SUCCESS:
                if self._session is not None:
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

    def _record(self, *, task: TaskName, provider: str, result: ProviderResult) -> None:
        if self._observe:
            default_observe_attempt(task=task, provider=provider, result=result, request_id=self._request_id)
        if self._recorder is not None:
            self._recorder(task=task, provider=provider, result=result, request_id=self._request_id)
