"""Observability package (D-019)."""

from opspilot.obs.tracing import LlmSpanAttrs, append_llm_jsonl, emit_llm_span

__all__ = ["LlmSpanAttrs", "append_llm_jsonl", "emit_llm_span"]
