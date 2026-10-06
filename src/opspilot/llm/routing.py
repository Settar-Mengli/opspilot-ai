"""Provider order and factory from env (INFERENCE_PROVIDER_ORDER)."""

from __future__ import annotations

import os
from collections.abc import Sequence

import httpx
from sqlalchemy.orm import Session

from opspilot.llm.circuit import CircuitBreaker
from opspilot.llm.operator_auth import OperatorAnthropicAuth
from opspilot.llm.providers.anthropic import (
    AnthropicProvider,
    anthropic_enabled,
    task_allowlisted,
)
from opspilot.llm.providers.base import LlmProvider
from opspilot.llm.providers.fake import FakeProvider
from opspilot.llm.providers.gemini import GeminiProvider
from opspilot.llm.providers.openai_compatible import OpenAICompatibleProvider
from opspilot.llm.types import TaskName

_DEFAULT_ORDER = ("gemini", "groq", "mistral", "cloudflare", "openrouter")
_OPENAI_COMPAT = frozenset({"groq", "mistral", "cloudflare", "openrouter", "ollama"})


def provider_order(raw: str | None = None) -> list[str]:
    """Parse INFERENCE_PROVIDER_ORDER; Anthropic never included from env order."""
    text = (raw if raw is not None else os.environ.get("INFERENCE_PROVIDER_ORDER", "")).strip()
    if not text:
        return list(_DEFAULT_ORDER)
    names = [p.strip().lower() for p in text.split(",") if p.strip()]
    return [n for n in names if n and n != "anthropic"]


def build_providers(
    order: Sequence[str] | None = None,
    *,
    client: httpx.Client | None = None,
    include_missing_keys: bool = False,
    operator_auth: OperatorAnthropicAuth | None = None,
    session: Session | None = None,
    task: TaskName | None = None,
) -> list[LlmProvider]:
    """Construct providers for the configured order.

    Providers without keys are skipped unless include_missing_keys (tests).
    Prepend ``AnthropicProvider`` only when ENABLED + operator auth + allowlisted task.
    Flag off → no Anthropic in the list (no anthropic llm_calls of any status).
    """
    names = list(order) if order is not None else provider_order()
    out: list[LlmProvider] = []
    for name in names:
        if name == "fake":
            out.append(FakeProvider())
            continue
        if name == "gemini":
            key = os.environ.get("GEMINI_API_KEY", "").strip()
            if key or include_missing_keys:
                out.append(GeminiProvider(api_key=key or "missing", client=client))
            continue
        if name in _OPENAI_COMPAT:
            if name == "cloudflare":
                ready = bool(os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()) and bool(
                    os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
                )
            elif name == "ollama":
                ready = True
            else:
                env_key = {
                    "groq": "GROQ_API_KEY",
                    "mistral": "MISTRAL_API_KEY",
                    "openrouter": "OPENROUTER_API_KEY",
                }[name]
                ready = bool(os.environ.get(env_key, "").strip())
            if ready or include_missing_keys:
                out.append(OpenAICompatibleProvider(name, client=client))
            continue
    if operator_auth is not None and anthropic_enabled() and task is not None and task_allowlisted(task):
        out.insert(
            0,
            AnthropicProvider(operator_auth=operator_auth, session=session),
        )
    return out


def filter_by_circuit(providers: Sequence[LlmProvider], circuit: CircuitBreaker) -> list[LlmProvider]:
    return [p for p in providers if not circuit.is_open(p.name)]
