"""Centralized runtime AI provider settings."""

from __future__ import annotations

import os

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class AISettings:
    """Resolve and hold AI provider settings for runtime usage."""

    def __init__(self) -> None:
        self._provider = self._resolve_provider()
        self._model = self._resolve_model()
        self._api_key = self._resolve_api_key()

    @staticmethod
    def _resolve_provider() -> str:
        provider = os.environ.get("OPSPILOT_AI_PROVIDER", DEFAULT_PROVIDER)
        normalized = provider.strip().lower()
        return normalized or DEFAULT_PROVIDER

    @staticmethod
    def _resolve_model() -> str:
        model = os.environ.get("OPSPILOT_AI_MODEL", DEFAULT_MODEL)
        normalized = model.strip()
        return normalized or DEFAULT_MODEL

    @staticmethod
    def _resolve_api_key() -> str | None:
        configured = os.environ.get("OPSPILOT_AI_API_KEY")
        if configured and configured.strip():
            return configured.strip()

        fallback = os.environ.get("ANTHROPIC_API_KEY")
        if fallback and fallback.strip():
            return fallback.strip()

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
