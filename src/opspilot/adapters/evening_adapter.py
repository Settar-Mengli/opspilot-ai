"""Evening adapter — thin wrapper over services.evening."""

from __future__ import annotations

from typing import Any

from opspilot.services.evening import generate_evening_summary as _generate_evening_summary

__all__ = ["generate_evening_summary"]


def generate_evening_summary(
    assistant_name: str = "OpsPilot",
    triage_records: list[dict[str, Any]] | None = None,
) -> str:
    return _generate_evening_summary(assistant_name, triage_records)
