"""Gemini native REST provider (generativelanguage.googleapis.com)."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from typing import Any

import httpx
from pydantic import BaseModel

from opspilot.llm.capabilities import JsonMode, json_mode_for
from opspilot.llm.model_defaults import GEMINI_DEFAULT_MODEL
from opspilot.llm.providers.http import default_timeout, map_http_provider_result
from opspilot.llm.schema_convert import gemini_response_schema, schema_prompt_fragment
from opspilot.llm.types import AttemptStatus, Message, ProviderResult, StreamChunk, TaskName

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def gemini_base_url() -> str:
    """REST API root (no trailing slash)."""
    return _GEMINI_BASE


def gemini_models_list_url() -> str:
    """Discover/probe endpoint for listing models."""
    return f"{_GEMINI_BASE}/models"


def resolve_gemini_model(task: TaskName, override: str | None = None) -> str:
    if override:
        return override
    task_key = f"GEMINI_MODEL_{task.upper()}"
    return os.environ.get(task_key) or os.environ.get("GEMINI_MODEL") or GEMINI_DEFAULT_MODEL


class GeminiProvider:
    """Gemini generateContent via REST (no Google SDK)."""

    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        base_url: str = _GEMINI_BASE,
    ) -> None:
        self._api_key = (api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")).strip()
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=default_timeout())
        self._base_url = base_url.rstrip("/")

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
        return self._generate(task=task, messages=messages, max_tokens=max_tokens, model=model, schema=None)

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
    ) -> ProviderResult:
        msgs = list(messages)
        if repair_hint:
            msgs.append(
                Message(
                    role="user",
                    content=(f"Fix JSON. Errors: {repair_hint}\n{schema_prompt_fragment(schema)}"),
                )
            )
        return self._generate(
            task=task,
            messages=msgs,
            max_tokens=max_tokens,
            model=model,
            schema=schema,
            force_json_object=force_json_object,
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

    def _generate(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int,
        model: str | None,
        schema: type[BaseModel] | None,
        force_json_object: bool = False,
    ) -> ProviderResult:
        if not self._api_key:
            return ProviderResult(status=AttemptStatus.ERROR, error_code="missing_api_key", model=model or "")

        resolved = resolve_gemini_model(task, model)
        url = f"{self._base_url}/models/{resolved}:generateContent"
        body: dict[str, Any] = {
            "contents": _to_gemini_contents(messages),
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if schema is not None:
            body["generationConfig"]["responseMimeType"] = "application/json"
            use_native = not force_json_object and json_mode_for(self.name, resolved) is JsonMode.NATIVE_SCHEMA
            if use_native:
                body["generationConfig"]["responseSchema"] = gemini_response_schema(schema)
            else:
                # JSON mime without schema — instruct via prompt fragment.
                body["contents"] = _to_gemini_contents(
                    [*messages, Message(role="user", content=schema_prompt_fragment(schema))]
                )

        started = time.perf_counter()
        try:
            response = self._client.post(url, params={"key": self._api_key}, json=body)
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
        text = _extract_text(data)
        usage = data.get("usageMetadata") or {}
        return ProviderResult(
            status=AttemptStatus.SUCCESS,
            text=text,
            model=resolved,
            input_tokens=int(usage.get("promptTokenCount") or 0),
            output_tokens=int(usage.get("candidatesTokenCount") or 0),
            latency_ms=latency_ms,
            raw={"finish": (data.get("candidates") or [{}])[0].get("finishReason")},
        )


def _to_gemini_contents(messages: list[Message]) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    for msg in messages:
        role = "user" if msg.role in {"user", "system"} else "model"
        contents.append({"role": role, "parts": [{"text": msg.content}]})
    return contents


def _extract_text(data: dict[str, Any]) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
    return "".join(texts)
