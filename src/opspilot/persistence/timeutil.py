"""ISO datetime helpers for persistence."""

from __future__ import annotations

from datetime import UTC, datetime


def parse_iso_utc(value: str | datetime | None) -> datetime | None:
    """Parse API/domain ISO strings into aware UTC datetimes."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def require_iso_utc(value: str | datetime) -> datetime:
    parsed = parse_iso_utc(value)
    if parsed is None:
        raise ValueError("expected ISO datetime")
    return parsed
