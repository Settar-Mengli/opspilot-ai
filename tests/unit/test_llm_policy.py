"""Unit tests for llm_allowed policy."""

from __future__ import annotations

import pytest

from opspilot.llm.policy import llm_allowed


@pytest.mark.parametrize(
    ("force", "disable", "expected"),
    [
        ("", "", True),
        ("0", "", True),
        ("1", "", False),
        ("true", "", False),
        ("", "1", False),
        ("", "yes", False),
        ("1", "1", False),
    ],
)
def test_llm_allowed_matrix(
    monkeypatch: pytest.MonkeyPatch,
    force: str,
    disable: str,
    expected: bool,
) -> None:
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", force)
    monkeypatch.setenv("OPSPILOT_LLM_DISABLE", disable)
    assert llm_allowed() is expected
