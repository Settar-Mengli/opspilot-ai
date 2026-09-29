"""Insights adapter — thin wrapper over services.insights."""

from __future__ import annotations

from typing import Any

from opspilot.services.insights import generate_insights as _generate_insights

__all__ = ["generate_insights"]


def generate_insights(
    assistant_name: str = "OpsPilot",
    triage_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _generate_insights(assistant_name, triage_records)
