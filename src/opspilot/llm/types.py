"""Shared LLM gateway types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

TaskName = Literal[
    "triage", "ask", "evening", "insights", "briefing", "demo_quality", "leaderboard", "judge_calibration"
]

MessageRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class Message:
    """One chat message."""

    role: MessageRole
    content: str


class AttemptStatus(StrEnum):
    """Per-attempt outcome recorded on LlmCall (C3+)."""

    SUCCESS = "success"
    ERROR = "error"
    RATE_LIMITED = "429"
    TIMEOUT = "timeout"
    BUDGET_DENIED = "budget_denied"
    POLICY_DENIED = "policy_denied"


@dataclass(frozen=True, slots=True)
class CompletionResult:
    """Successful prose completion."""

    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    prompt_version: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StreamChunk:
    """One streamed token/delta event (prose-only)."""

    text: str
    provider: str
    model: str
    done: bool = False


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """Raw provider attempt outcome before gateway failover logic."""

    status: AttemptStatus
    text: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    error_code: str | None = None
    retry_after_s: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)
