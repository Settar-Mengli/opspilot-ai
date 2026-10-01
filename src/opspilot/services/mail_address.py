"""Validate and format email addr-specs for HITL send headers (D-033)."""

from __future__ import annotations

import re
from email.headerregistry import Address
from email.utils import getaddresses, parseaddr

_CTRL_OR_CRLF = re.compile(r"[\x00-\x1f\x7f]")


class MailAddressError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _has_unsafe_chars(value: str) -> bool:
    return bool(_CTRL_OR_CRLF.search(value))


def parse_single_addr_spec(raw: str) -> str:
    """Return a single normalized addr-spec (lowercased local@domain).

    Rejects CR/LF/controls in display name or address, empty/invalid syntax,
    and multi-address inputs when one address is expected.
    """
    text = (raw or "").strip()
    if not text:
        raise MailAddressError("empty_address")
    if _has_unsafe_chars(text):
        raise MailAddressError("unsafe_address_chars")

    parsed = getaddresses([text])
    if len(parsed) != 1:
        raise MailAddressError("multiple_addresses")
    display, addr = parsed[0]
    display = (display or "").strip()
    addr = (addr or "").strip()
    if not addr or "@" not in addr:
        # parseaddr fallback for bare specs
        _d, addr2 = parseaddr(text)
        display = display or (_d or "").strip()
        addr = (addr2 or "").strip()
    if not addr or "@" not in addr or addr.startswith("@") or addr.endswith("@"):
        raise MailAddressError("invalid_address")
    if _has_unsafe_chars(display) or _has_unsafe_chars(addr):
        raise MailAddressError("unsafe_address_chars")
    # Reject quoted local tricks with spaces that slipped through
    if any(c.isspace() for c in addr):
        raise MailAddressError("invalid_address")
    return addr.lower()


def format_to_header(addr_spec: str) -> str:
    """Build a To: header value via Address/formataddr (no raw From strings)."""
    normalized = parse_single_addr_spec(addr_spec)
    local, _, domain = normalized.partition("@")
    return str(Address(username=local, domain=domain))


def assert_safe_subject(subject: str) -> str:
    text = subject if isinstance(subject, str) else str(subject)
    if _has_unsafe_chars(text) or "\n" in text or "\r" in text:
        raise MailAddressError("unsafe_subject")
    return text
