"""CLI smoke for hermetic run_evals (C9)."""

from __future__ import annotations

from pathlib import Path

from opspilot.jobs.run_evals import main, run_hermetic


def test_run_hermetic_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "hermetic.json"
    payload = run_hermetic(out=out)
    assert out.is_file()
    assert payload["mode"] == "hermetic"
    assert payload["n_triage"] == 40
    assert payload["n_redteam"] == 20
    assert payload["n_ask_agent"] == 7
    assert payload["n_redteam_agent"] == 5
    assert payload["gate_passed"] is True
    assert "confusion" in payload


def test_cli_hermetic_exit_zero(tmp_path: Path) -> None:
    out = tmp_path / "cli.json"
    assert main(["--out", str(out)]) == 0
    assert out.is_file()


def test_cli_rejects_provider_without_live() -> None:
    assert main(["--provider", "gemini"]) == 2


def test_cli_live_without_provider_exits_2() -> None:
    assert main(["--live"]) == 2
