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
from opspilot.llm.model_defaults import (
    CLOUDFLARE_DEFAULT_MODEL,
    GROQ_DEFAULT_MODEL,
    MISTRAL_DEFAULT_MODEL,
    OLLAMA_DEFAULT_MODEL,
    OPENROUTER_DEFAULT_MODEL,
)
from opspilot.llm.providers.http import default_timeout, map_http_provider_result
from opspilot.llm.schema_convert import groq_strict_schema, schema_prompt_fragment
from opspilot.llm.types import AttemptStatus, Message, ProviderResult, StreamChunk, TaskName

_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
        "default_model": GROQ_DEFAULT_MODEL,
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "key_env": "MISTRAL_API_KEY",
        "model_env": "MISTRAL_MODEL",
        "default_model": MISTRAL_DEFAULT_MODEL,
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "default_model": OPENROUTER_DEFAULT_MODEL,
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434/v1",
        "key_env": "OLLAMA_API_KEY",
        "model_env": "OLLAMA_MODEL",
        "default_model": OLLAMA_DEFAULT_MODEL,
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


_TRUTHY = frozenset({"1", "true", "yes", "on"})


def openrouter_allow_paid() -> bool:
    return os.environ.get("OPSPILOT_OPENROUTER_ALLOW_PAID", "").strip().lower() in _TRUTHY


def openrouter_model_denied(model: str) -> str | None:
    """Return error_code if OpenRouter model is non-:free and paid-allow is off."""
    if model.endswith(":free"):
        return None
    if openrouter_allow_paid():
        return None
    return "openrouter_paid_model_denied"


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
            default_model=CLOUDFLARE_DEFAULT_MODEL,
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
        force_json_object: bool = False,
        temperature: float | None = None,
    ) -> ProviderResult:
        msgs = list(messages)
        if repair_hint:
            msgs.append(
                Message(
                    role="user",
                    content=f"Fix JSON. Errors: {repair_hint}\n{schema_prompt_fragment(schema)}",
                )
            )
        return self._chat(
            task=task,
            messages=msgs,
            max_tokens=max_tokens,
            model=model,
            schema=schema,
            force_json_object=force_json_object,
            temperature=temperature,
        )

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
        force_json_object: bool = False,
        temperature: float | None = None,
    ) -> ProviderResult:
        cfg = self._config
        if cfg.name != "ollama" and not cfg.api_key:
            return ProviderResult(status=AttemptStatus.ERROR, error_code="missing_api_key", model=model or "")

        resolved = resolve_task_model(cfg.name, task, model, cfg.model_env, cfg.default_model)
        if cfg.name == "openrouter":
            denied = openrouter_model_denied(resolved)
            if denied:
                return ProviderResult(
                    status=AttemptStatus.ERROR,
                    model=resolved,
                    error_code=denied,
                )
        url = f"{cfg.base_url.rstrip('/')}/chat/completions"
        body: dict[str, Any] = {
            "model": resolved,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            body["temperature"] = temperature
        mode = JsonMode.JSON_OBJECT if force_json_object else json_mode_for(cfg.name, resolved)
        if schema is not None:
            # Always remind the model of exact field names for json_object / repair paths.
            body["messages"] = [
                *body["messages"],
                {"role": "user", "content": schema_prompt_fragment(schema)},
            ]
            if mode is JsonMode.NATIVE_SCHEMA:
                body["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema.__name__,
                        "schema": groq_strict_schema(schema),
                        "strict": True,
                    },
                }
            elif mode is JsonMode.JSON_OBJECT:
                body["response_format"] = {"type": "json_object"}
            else:
                pass  # prompt fragment already appended

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
        mapped = map_http_provider_result(response=response, model=resolved, latency_ms=latency_ms)
        if mapped is not None:
            return mapped

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
