"""Conversation adapter — thin wrapper over services.ask (legacy import path)."""

from __future__ import annotations

from typing import Any

from opspilot.services.ask import answer_question as _answer_question

__all__ = ["answer_question"]


def answer_question(
    question: str,
    assistant_name: str = "OpsPilot",
    triage_records: list[dict[str, Any]] | None = None,
) -> str:
    return _answer_question(question, assistant_name, triage_records)
