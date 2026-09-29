"""Capability map for structured-output modes (D-013)."""

from __future__ import annotations

from enum import StrEnum


class JsonMode(StrEnum):
    """How a provider prefers to emit JSON."""

    NATIVE_SCHEMA = "native_schema"  # Gemini responseSchema / Groq strict
    JSON_OBJECT = "json_object"  # response_format json_object
    PROMPT_ONLY = "prompt_only"  # instruct in prompt only


# Default capability map; Groq strict only when model id looks like a known strict model.
_PROVIDER_JSON: dict[str, JsonMode] = {
    "gemini": JsonMode.NATIVE_SCHEMA,
    "groq": JsonMode.JSON_OBJECT,
    "mistral": JsonMode.JSON_OBJECT,
    "cloudflare": JsonMode.JSON_OBJECT,
    "openrouter": JsonMode.JSON_OBJECT,
    "ollama": JsonMode.PROMPT_ONLY,
    "fake": JsonMode.PROMPT_ONLY,
    "anthropic": JsonMode.PROMPT_ONLY,
}

_GROQ_STRICT_PREFIXES = ("openai/gpt-oss",)


def json_mode_for(provider: str, model: str | None = None) -> JsonMode:
    """Return the preferred JSON mode for provider (+ optional model)."""
    name = provider.strip().lower()
    if name == "groq" and model and any(model.startswith(p) for p in _GROQ_STRICT_PREFIXES):
        return JsonMode.NATIVE_SCHEMA
    return _PROVIDER_JSON.get(name, JsonMode.PROMPT_ONLY)
