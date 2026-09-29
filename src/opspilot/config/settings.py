"""Centralized runtime AI provider settings (legacy surface for /settings).

Ask/evening/insights/triage/briefing use the llm/ gateway + free-tier env keys.
This module remains for the read-only settings payload until B4 settings redesign.
"""

from __future__ import annotations

import os

DEFAULT_PROVIDER = "gemini"
DEFAULT_MODEL = "gemini-2.0-flash-lite"


class AISettings:
    """Resolve and hold AI provider settings for runtime usage."""

    def __init__(self) -> None:
        self._provider = self._resolve_provider()
        self._model = self._resolve_model()
        self._api_key = self._resolve_api_key()

    @staticmethod
    def _resolve_provider() -> str:
        order = os.environ.get("INFERENCE_PROVIDER_ORDER", "").strip()
        if order:
            first = order.split(",")[0].strip().lower()
            if first and first != "anthropic":
                return first
        provider = os.environ.get("OPSPILOT_AI_PROVIDER", DEFAULT_PROVIDER)
        normalized = provider.strip().lower()
        if normalized == "anthropic":
            return DEFAULT_PROVIDER
        return normalized or DEFAULT_PROVIDER

    @staticmethod
    def _resolve_model() -> str:
        provider = AISettings._resolve_provider()
        env_map = {
            "gemini": "GEMINI_MODEL",
            "groq": "GROQ_MODEL",
            "mistral": "MISTRAL_MODEL",
            "openrouter": "OPENROUTER_MODEL",
            "cloudflare": "CLOUDFLARE_MODEL",
            "ollama": "OLLAMA_MODEL",
        }
        model_env = env_map.get(provider)
        if model_env:
            configured = os.environ.get(model_env, "").strip()
            if configured:
                return configured
        legacy = os.environ.get("OPSPILOT_AI_MODEL", "").strip()
        return legacy or DEFAULT_MODEL

    @staticmethod
    def _resolve_api_key() -> str | None:
        for name in (
            "GEMINI_API_KEY",
            "GROQ_API_KEY",
            "MISTRAL_API_KEY",
            "OPENROUTER_API_KEY",
            "CLOUDFLARE_API_TOKEN",
            "OPSPILOT_AI_API_KEY",
        ):
            configured = os.environ.get(name)
            if configured and configured.strip():
                return configured.strip()
        return None

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
