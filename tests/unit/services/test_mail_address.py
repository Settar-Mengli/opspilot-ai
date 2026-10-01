"""Mail address / subject header safety (D-033)."""

from __future__ import annotations

import pytest

from opspilot.services.mail_address import (
    MailAddressError,
    assert_safe_subject,
    format_to_header,
    parse_single_addr_spec,
)


def test_parse_normalizes_and_lowercases() -> None:
    assert parse_single_addr_spec("  Demo User <Demo@Example.COM> ") == "demo@example.com"


def test_reject_crlf_bcc_smuggle_in_display_name() -> None:
    hostile = "Evil\r\nBcc: attacker@evil.com\r\n <victim@example.com>"
    with pytest.raises(MailAddressError) as exc:
        parse_single_addr_spec(hostile)
    assert exc.value.code == "unsafe_address_chars"


def test_reject_multiple_addresses() -> None:
    with pytest.raises(MailAddressError) as exc:
        parse_single_addr_spec("a@example.com, b@example.com")
    assert exc.value.code == "multiple_addresses"


def test_reject_empty_and_invalid() -> None:
    with pytest.raises(MailAddressError):
        parse_single_addr_spec("")
    with pytest.raises(MailAddressError):
        parse_single_addr_spec("not-an-email")


def test_format_to_header_uses_addr_spec_only() -> None:
    header = format_to_header("Name <Ops@Example.com>")
    assert header == "ops@example.com"
    assert "\n" not in header and "\r" not in header


def test_assert_safe_subject_rejects_newline_and_bcc_smuggle() -> None:
    with pytest.raises(MailAddressError) as exc:
        assert_safe_subject("Hello\nBcc: evil@x.com")
    assert exc.value.code == "unsafe_subject"
    with pytest.raises(MailAddressError):
        assert_safe_subject("Hello\r\nBcc: evil@x.com")
    assert assert_safe_subject("Re: Hello") == "Re: Hello"
