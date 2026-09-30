"""Discover/probe URL helpers — sole source of provider hosts for llm_discover."""

from __future__ import annotations

from opspilot.llm.providers.gemini import gemini_models_list_url
from opspilot.llm.providers.openai_compatible import config_for, ollama_tags_url

__all__ = [
    "gemini_models_list_url",
    "openai_compat_models_url",
    "ollama_tags_url",
]


def openai_compat_models_url(provider: str) -> str:
    """GET …/models URL for an OpenAI-compatible provider (groq/mistral/openrouter/…)."""
    base = config_for(provider).base_url.rstrip("/")
    return f"{base}/models"
