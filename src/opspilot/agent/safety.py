"""Agent safety helpers — UNTRUSTED wrapping for tool outputs."""

from __future__ import annotations

from opspilot.llm.prompt_safety import neutralize_text, wrap_untrusted


def tool_result_untrusted(tool_name: str, raw: str, *, max_chars: int = 2000) -> str:
    body = neutralize_text(raw)[:max_chars]
    return wrap_untrusted(f"tool:{tool_name}", body)
