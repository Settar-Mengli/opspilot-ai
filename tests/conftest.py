"""Shared pytest fixtures for hermetic, order-independent tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _force_rules_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force rule-based triage for every test; subprocesses inherit this env."""
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")


@pytest.fixture(autouse=True)
def _block_real_anthropic_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the suite if anthropic.Anthropic is constructed during a test.

    Conversation-adapter unit tests replace Anthropic on their own module; that
    still goes through this wrapper when they import the real symbol first.
    Replacing ``anthropic.Anthropic`` here keeps the guard global.
    """
    import anthropic

    def _forbidden(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(
            "anthropic.Anthropic must not be constructed during tests "
            "(OPSPILOT_FORCE_RULES / hermetic guard)"
        )

    monkeypatch.setattr(anthropic, "Anthropic", _forbidden)
