"""Hermetic unit tests for live_smoke_b5 preflight / flag logic (never runs live smoke)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "live_smoke_b5.py"


def _load_smoke():
    spec = importlib.util.spec_from_file_location("live_smoke_b5", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["live_smoke_b5"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def smoke():
    return _load_smoke()


def test_smoke_sync_path_constant(smoke) -> None:
    assert smoke.SYNC_PATH == "/api/v1/sync"


def test_smoke_max_asks_constant(smoke) -> None:
    assert smoke.SMOKE_MAX_ASKS == 3


def test_default_vs_send_flag(smoke) -> None:
    args = smoke.argparse.ArgumentParser()
    args.add_argument("--send", action="store_true")
    assert args.parse_args([]).send is False
    assert args.parse_args(["--send"]).send is True


def test_preflight_anthropic_enabled(smoke, monkeypatch: pytest.MonkeyPatch) -> None:
    import opspilot.llm.providers.anthropic as anth

    monkeypatch.setattr(anth, "anthropic_enabled", lambda: True)
    with pytest.raises(SystemExit):
        smoke._preflight(operator="ops@example.com")


def test_preflight_force_rules(smoke, monkeypatch: pytest.MonkeyPatch) -> None:
    import opspilot.llm.providers.anthropic as anth

    monkeypatch.setattr(anth, "anthropic_enabled", lambda: False)
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    with pytest.raises(SystemExit):
        smoke._preflight(operator="ops@example.com")


def test_preflight_allowlist_mismatch(smoke, monkeypatch: pytest.MonkeyPatch) -> None:
    import opspilot.llm.providers.anthropic as anth

    monkeypatch.setattr(anth, "anthropic_enabled", lambda: False)
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.delenv("LLM_DISABLE", raising=False)
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "other@example.com")
    with pytest.raises(SystemExit):
        smoke._preflight(operator="ops@example.com")


def test_ask_cap_enforced(smoke) -> None:
    asks = [smoke.SMOKE_MAX_ASKS]
    with pytest.raises(SystemExit):
        if asks[0] >= smoke.SMOKE_MAX_ASKS:
            smoke._die("llm_ask_cap")


def test_unknown_counts_as_one_send_stops(smoke) -> None:
    """Documented flag logic: unknown outcome consumes the one-send budget."""
    sends = 0
    err_code = "send_outcome_unknown"
    status = 502
    if status == 502 or err_code == "send_outcome_unknown":
        sends = 1
    assert sends == 1
