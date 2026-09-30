"""Hermetic tests for eval result JSON writer (D4 Path/str fix)."""

from __future__ import annotations

from pathlib import Path

from opspilot.evals.report import write_eval_json


def test_write_eval_json_accepts_path(tmp_path: Path) -> None:
    out = tmp_path / "sub" / "result.json"
    written = write_eval_json(out, {"mode": "hermetic", "n": 1})
    assert written == out
    assert out.is_file()
    assert '"mode": "hermetic"' in out.read_text(encoding="utf-8")


def test_write_eval_json_accepts_str_path(tmp_path: Path) -> None:
    """Regression: D4 helper passed a str and crashed after a full Cloudflare burn."""
    out = tmp_path / "via-str" / "live.json"
    written = write_eval_json(str(out), {"provider": "cloudflare", "accepted": 33})
    assert written == out
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert '"provider": "cloudflare"' in text
    assert written.parent.is_dir()
