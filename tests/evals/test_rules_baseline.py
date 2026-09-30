"""Hermetic rules-vs-labels report (no CI floor until STOP F1-FLOOR)."""

from __future__ import annotations

from opspilot.evals.rules_baseline import format_hit_report, run_rules_vs_labels


def test_rules_vs_labels_report_runs() -> None:
    report = run_rules_vs_labels()
    assert report["n"] == 40
    assert "macro_f1" in report
    for field in ("urgency", "category", "sentiment"):
        assert "hits" in report["fields"][field]
    # Printed for owner review at STOP F1-FLOOR (A2 leakage signal).
    print("\n" + format_hit_report(report))
