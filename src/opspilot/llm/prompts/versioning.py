"""Prompt version labels and sha256 fingerprints for LlmCall (ROADMAP B2)."""

from __future__ import annotations

import hashlib

from opspilot.llm.types import Message, TaskName

# Static template revision per task (bump when system/user templates change materially).
PROMPT_LABELS: dict[TaskName, str] = {
    "ask": "ask/v1",
    "evening": "evening/v1",
    "insights": "insights/v1",
    "triage": "triage/v1",
    "briefing": "briefing/v1",
    "demo_quality": "demo_quality/v1",
    "leaderboard": "leaderboard/v1",
    "judge_calibration": "judge_calibration/v1",
}


def prompt_version_sha256(*, task: TaskName, messages: list[Message]) -> str:
    """sha256(label + roles/contents) — stored in LlmCall.prompt_version (64 hex)."""
    label = PROMPT_LABELS.get(task, f"{task}/v1")
    canonical = label + "\n" + "\n".join(f"{m.role}:{m.content}" for m in messages)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
