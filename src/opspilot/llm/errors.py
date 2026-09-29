"""LLM gateway errors."""

from __future__ import annotations


class LlmError(Exception):
    """Base LLM gateway error."""


class LlmPolicyDenied(LlmError):
    """Remote LLM blocked by FORCE_RULES / LLM_DISABLE / visitor policy."""


class LlmProvidersExhausted(LlmError):
    """All providers failed or were skipped."""


class LlmSchemaError(LlmError):
    """Structured output failed validation after repair."""
