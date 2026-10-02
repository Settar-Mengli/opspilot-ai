"""Recipient allowlist for HITL send (D-033 / D-B5-8)."""

from __future__ import annotations

import os

from opspilot.services.mail_address import MailAddressError, parse_single_addr_spec


def send_recipient_allowlist() -> frozenset[str] | None:
    """Return normalized allowlist set, or None when unset (deny-all)."""
    raw = os.environ.get("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "").strip()
    if not raw:
        return None
    out: set[str] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(parse_single_addr_spec(part))
        except MailAddressError:
            continue
    return frozenset(out) if out else None


def recipients_allowed(to_addrs: str) -> bool:
    """True only when every address is on the allowlist. Unset allowlist ⇒ deny."""
    allow = send_recipient_allowlist()
    if allow is None:
        return False
    try:
        addr = parse_single_addr_spec(to_addrs)
    except MailAddressError:
        return False
    return addr in allow
