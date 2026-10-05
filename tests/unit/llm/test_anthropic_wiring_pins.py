"""Cross-cutting Anthropic pins (C7): A6 minting, morning.yml, L1 out-of-scope."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from opspilot.jobs.morning_run import PreflightError, _preflight
from opspilot.llm.operator_auth import OperatorAnthropicAuth
from opspilot.llm.routing import build_providers


def test_from_session_only_in_ask_and_oauth_routes() -> None:
    """A6: OperatorAnthropicAuth.from_session call sites limited to Ask + Sync routes."""
    root = Path("src/opspilot")
    call_files: set[str] = set()
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "from_session":
                call_files.add(path.as_posix())
    assert call_files == {
        "src/opspilot/api/v1/routes_ask.py",
        "src/opspilot/api/v1/oauth_routes.py",
    }


def test_morning_yml_anthropic_literal_false() -> None:
    text = Path(".github/workflows/morning.yml").read_text(encoding="utf-8")
    assert 'OPSPILOT_ANTHROPIC_ENABLED: "false"' in text


def test_morning_preflight_anthropic_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    with pytest.raises(PreflightError, match="anthropic_enabled"):
        _preflight()


def test_legacy_ask_never_prepends_anthropic() -> None:
    providers = build_providers(order=["fake"], operator_auth=None)
    assert all(p.name != "anthropic" for p in providers)


def test_post_runs_triage_no_anthropic() -> None:
    """Pipeline / post-runs triage builders never receive operator auth prepend."""
    providers = build_providers(order=["fake"])
    assert all(p.name != "anthropic" for p in providers)


def test_evening_insights_briefing_no_anthropic_even_with_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even with auth + ENABLED, non-ask/triage tasks stay gated off."""
    from opspilot.llm.providers.anthropic import gate_reason

    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN", "1")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_OUT", "5")
    auth = OperatorAnthropicAuth(role="demo_operator")
    assert gate_reason("evening", operator_auth=auth) == "task_not_allowlisted"  # type: ignore[arg-type]
    assert gate_reason("insights", operator_auth=auth) == "task_not_allowlisted"  # type: ignore[arg-type]
    assert gate_reason("briefing", operator_auth=auth) == "task_not_allowlisted"  # type: ignore[arg-type]


def test_evals_live_marks_anthropic_skipped() -> None:
    text = Path("src/opspilot/evals/live.py").read_text(encoding="utf-8")
    assert '"anthropic": "skipped"' in text or "'anthropic': 'skipped'" in text


def test_operator_anthropic_auth_none_session() -> None:
    assert OperatorAnthropicAuth.from_session(None) is None
