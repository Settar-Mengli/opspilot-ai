"""Centralized runtime AI provider settings (legacy surface for /settings).

Ask/evening/insights/triage/briefing use the llm/ gateway + free-tier env keys.
This module remains for the read-only settings payload until B4 settings redesign.
Retired legacy provider/model/key env vars (pre-gateway) are ignored.
"""

from __future__ import annotations

import os

from opspilot.llm.model_defaults import DEFAULT_MODELS, GEMINI_DEFAULT_MODEL

DEFAULT_PROVIDER = "gemini"
DEFAULT_MODEL = GEMINI_DEFAULT_MODEL

_MODEL_ENV: dict[str, str] = {
    "gemini": "GEMINI_MODEL",
    "groq": "GROQ_MODEL",
    "mistral": "MISTRAL_MODEL",
    "openrouter": "OPENROUTER_MODEL",
    "cloudflare": "CLOUDFLARE_MODEL",
    "ollama": "OLLAMA_MODEL",
}

_KEY_ENV: dict[str, str] = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "cloudflare": "CLOUDFLARE_API_TOKEN",
    "ollama": "OLLAMA_API_KEY",
}


def _provider_order() -> list[str]:
    raw = os.environ.get("INFERENCE_PROVIDER_ORDER", "").strip()
    if not raw:
        return [DEFAULT_PROVIDER]
    names = [p.strip().lower() for p in raw.split(",") if p.strip()]
    return [n for n in names if n and n != "anthropic"] or [DEFAULT_PROVIDER]


def _key_for(provider: str) -> str | None:
    if provider == "cloudflare":
        token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        if token and account:
            return token
        return None
    if provider == "ollama":
        # Local; treat as configured without a key.
        return os.environ.get("OLLAMA_API_KEY", "").strip() or "local"
    env_name = _KEY_ENV.get(provider)
    if not env_name:
        return None
    value = os.environ.get(env_name, "").strip()
    return value or None


def _model_for(provider: str) -> str:
    env_name = _MODEL_ENV.get(provider)
    if env_name:
        configured = os.environ.get(env_name, "").strip()
        if configured:
            return configured
    return DEFAULT_MODELS.get(provider, DEFAULT_MODEL)


class AISettings:
    """Resolve and hold AI provider settings for runtime usage."""

    def __init__(self) -> None:
        self._provider = self._resolve_provider()
        self._model = self._resolve_model()
        self._api_key = self._resolve_api_key()

    @staticmethod
    def _resolve_provider() -> str:
        order = _provider_order()
        for name in order:
            if _key_for(name):
                return name
        return order[0]

    @staticmethod
    def _resolve_model() -> str:
        return _model_for(AISettings._resolve_provider())

    @staticmethod
    def _resolve_api_key() -> str | None:
        provider = AISettings._resolve_provider()
        key = _key_for(provider)
        if provider == "ollama" and key == "local":
            return None
        return key

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    @property
    def api_key(self) -> str | None:
        return self._api_key

    def override(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """Override settings at runtime without process restart."""
        if provider is not None:
            normalized_provider = provider.strip().lower()
            self._provider = normalized_provider or DEFAULT_PROVIDER

        if model is not None:
            normalized_model = model.strip()
            self._model = normalized_model or DEFAULT_MODEL

        if api_key is not None:
            normalized_key = api_key.strip()
            self._api_key = normalized_key or None


ai_settings = AISettings()
