"""OpenAI-compatible chat completions (groq / mistral / cloudflare / openrouter / ollama)."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel

from opspilot.llm.capabilities import JsonMode, json_mode_for
from opspilot.llm.providers.http import default_timeout, parse_retry_after
from opspilot.llm.types import AttemptStatus, Message, ProviderResult, StreamChunk, TaskName

_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
        "default_model": "llama-3.1-8b-instant",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "key_env": "MISTRAL_API_KEY",
        "model_env": "MISTRAL_MODEL",
        "default_model": "mistral-small-latest",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "default_model": "openrouter/auto",
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434/v1",
        "key_env": "OLLAMA_API_KEY",
        "model_env": "OLLAMA_MODEL",
        "default_model": "llama3.2",
    },
}


@dataclass(frozen=True, slots=True)
class OpenAICompatibleConfig:
    name: str
    base_url: str
    api_key: str
    model_env: str
    default_model: str
    extra_headers: dict[str, str]


def resolve_task_model(provider: str, task: TaskName, override: str | None, model_env: str, default: str) -> str:
    if override:
        return override
    task_env = f"{model_env}_{task.upper()}"
    return os.environ.get(task_env) or os.environ.get(model_env) or default


def ollama_native_base_url() -> str:
    """Ollama native (non-/v1) root for /api/tags discover probes."""
    return (os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")


def ollama_tags_url() -> str:
    return f"{ollama_native_base_url()}/api/tags"


def config_for(provider: str) -> OpenAICompatibleConfig:
    name = provider.strip().lower()
    if name == "cloudflare":
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        base = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1"
        return OpenAICompatibleConfig(
            name="cloudflare",
            base_url=base,
            api_key=token,
            model_env="CLOUDFLARE_MODEL",
            default_model="@cf/meta/llama-3.1-8b-instruct",
            extra_headers={},
        )
    defaults = _PROVIDER_DEFAULTS.get(name)
    if defaults is None:
        raise ValueError(f"unsupported openai-compatible provider: {provider}")
    base_url = defaults["base_url"]
    if name == "ollama":
        base_url = ollama_native_base_url()
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
    return OpenAICompatibleConfig(
        name=name,
        base_url=base_url,
        api_key=os.environ.get(defaults["key_env"], "").strip(),
        model_env=defaults["model_env"],
        default_model=defaults["default_model"],
        extra_headers={},
    )


class OpenAICompatibleProvider:
    """Single client class configured per OpenAI-compatible host."""

    def __init__(
        self,
        provider: str,
        *,
        client: httpx.Client | None = None,
        config: OpenAICompatibleConfig | None = None,
    ) -> None:
        self._config = config or config_for(provider)
        self.name = self._config.name
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=default_timeout())

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def complete(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int,
        model: str | None = None,
    ) -> ProviderResult:
        return self._chat(task=task, messages=messages, max_tokens=max_tokens, model=model, schema=None)

    def complete_json(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        schema: type[BaseModel],
        max_tokens: int,
        model: str | None = None,
        repair_hint: str | None = None,
    ) -> ProviderResult:
        msgs = list(messages)
        if repair_hint:
            msgs.append(Message(role="user", content=f"Fix JSON. Errors: {repair_hint}"))
        return self._chat(task=task, messages=msgs, max_tokens=max_tokens, model=model, schema=schema)

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

    def _chat(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int,
        model: str | None,
        schema: type[BaseModel] | None,
    ) -> ProviderResult:
        cfg = self._config
        if cfg.name != "ollama" and not cfg.api_key:
            return ProviderResult(status=AttemptStatus.ERROR, error_code="missing_api_key", model=model or "")

        resolved = resolve_task_model(cfg.name, task, model, cfg.model_env, cfg.default_model)
        url = f"{cfg.base_url.rstrip('/')}/chat/completions"
        body: dict[str, Any] = {
            "model": resolved,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
        }
        mode = json_mode_for(cfg.name, resolved)
        if schema is not None:
            if mode is JsonMode.NATIVE_SCHEMA:
                body["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema(), "strict": True},
                }
            elif mode is JsonMode.JSON_OBJECT:
                body["response_format"] = {"type": "json_object"}
            else:
                body["messages"] = [
                    *body["messages"],
                    {"role": "user", "content": "Respond with JSON only matching the requested schema."},
                ]

        headers = {"Content-Type": "application/json", **cfg.extra_headers}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"

        started = time.perf_counter()
        try:
            response = self._client.post(url, headers=headers, json=body)
        except httpx.TimeoutException:
            return ProviderResult(
                status=AttemptStatus.TIMEOUT,
                model=resolved,
                error_code="timeout",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:  # noqa: BLE001 — include pytest-socket blocks
            return ProviderResult(
                status=AttemptStatus.ERROR,
                model=resolved,
                error_code=type(exc).__name__,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code == 429:
            return ProviderResult(
                status=AttemptStatus.RATE_LIMITED,
                model=resolved,
                error_code="429",
                retry_after_s=parse_retry_after(response),
                latency_ms=latency_ms,
            )
        if response.status_code >= 400:
            return ProviderResult(
                status=AttemptStatus.ERROR,
                model=resolved,
                error_code=f"http_{response.status_code}",
                latency_ms=latency_ms,
            )

        data = response.json()
        choices = data.get("choices") or []
        text = ""
        if choices:
            text = str((choices[0].get("message") or {}).get("content") or "")
        usage = data.get("usage") or {}
        return ProviderResult(
            status=AttemptStatus.SUCCESS,
            text=text,
            model=resolved,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            latency_ms=latency_ms,
            raw={"finish": choices[0].get("finish_reason") if choices else None},
        )
