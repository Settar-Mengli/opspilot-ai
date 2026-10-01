"""Hermetic Google OAuth scope validation (never invent scopes)."""

from __future__ import annotations

from typing import Any

import pytest

from opspilot.integrations.google_oauth import (
    IncompleteGrantError,
    TokenBundle,
    complete_oauth,
    has_required_scopes,
)


class _FakeExchanger:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def exchange(self, *, code: str, code_verifier: str, redirect_uri: str) -> dict[str, Any]:
        _ = code, code_verifier, redirect_uri
        return self._payload

    def fetch_email(self, *, access_token: str) -> str:
        _ = access_token
        return "demo@example.com"


FULL_SCOPES = (
    "openid email https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar.readonly"
)


def test_has_required_scopes() -> None:
    assert has_required_scopes(FULL_SCOPES) is True
    assert has_required_scopes("https://www.googleapis.com/auth/gmail.readonly") is False
    assert has_required_scopes("") is False


def test_complete_oauth_rejects_missing_scope_key() -> None:
    ex = _FakeExchanger({"refresh_token": "r", "access_token": "a"})
    with pytest.raises(IncompleteGrantError, match="missing_scope"):
        complete_oauth(code="c", code_verifier="v", exchanger=ex)


def test_complete_oauth_rejects_empty_scope() -> None:
    ex = _FakeExchanger({"refresh_token": "r", "access_token": "a", "scope": ""})
    with pytest.raises(IncompleteGrantError, match="missing_scope"):
        complete_oauth(code="c", code_verifier="v", exchanger=ex)


def test_complete_oauth_rejects_incomplete_grant() -> None:
    ex = _FakeExchanger(
        {
            "refresh_token": "r",
            "access_token": "a",
            "scope": "openid email https://www.googleapis.com/auth/gmail.readonly",
        }
    )
    with pytest.raises(IncompleteGrantError, match="incomplete_grant"):
        complete_oauth(code="c", code_verifier="v", exchanger=ex)


def test_complete_oauth_accepts_full_grant() -> None:
    ex = _FakeExchanger({"refresh_token": "r", "access_token": "a", "scope": FULL_SCOPES})
    bundle = complete_oauth(code="c", code_verifier="v", exchanger=ex)
    assert isinstance(bundle, TokenBundle)
    assert bundle.email == "demo@example.com"
    assert has_required_scopes(bundle.scopes)
