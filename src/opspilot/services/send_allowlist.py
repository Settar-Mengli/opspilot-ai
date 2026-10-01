"""Recipient allowlist for HITL send (D-033 / D-B5-8)."""

from __future__ import annotations

import os


def send_recipient_allowlist() -> frozenset[str] | None:
    """Return allowlist set, or None when unset (deny-all)."""
    raw = os.environ.get("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "").strip()
    if not raw:
        return None
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def recipients_allowed(to_addrs: str) -> bool:
    """True only when every address is on the allowlist. Unset allowlist ⇒ deny."""
    allow = send_recipient_allowlist()
    if allow is None:
        return False
    addrs = [a.strip().lower() for a in to_addrs.replace(";", ",").split(",") if a.strip()]
    if not addrs:
        return False
    return all(a in allow for a in addrs)
