"""Send allowlist normalization (D-033)."""

from __future__ import annotations

import pytest

from opspilot.services.send_allowlist import recipients_allowed, send_recipient_allowlist


def test_unset_allowlist_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", raising=False)
    assert send_recipient_allowlist() is None
    assert recipients_allowed("demo@example.com") is False


def test_empty_allowlist_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "  ,  ")
    assert send_recipient_allowlist() is None
    assert recipients_allowed("demo@example.com") is False


def test_case_insensitive_trimmed_display_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", " Demo User <Demo@Example.COM> ")
    assert send_recipient_allowlist() == frozenset({"demo@example.com"})
    assert recipients_allowed("demo@example.com") is True
    assert recipients_allowed("DEMO@example.com") is True
    assert recipients_allowed("other@example.com") is False
