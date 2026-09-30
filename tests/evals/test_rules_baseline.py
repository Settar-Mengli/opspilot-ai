"""Hermetic rules-vs-labels CI gate (macro-F1 floor locked at STOP F1-FLOOR)."""

from __future__ import annotations

from opspilot.evals.rules_baseline import MACRO_F1_FLOOR, format_hit_report, run_rules_vs_labels
from opspilot.evals.scorer import score_triage_fields


def test_rules_vs_labels_meets_macro_f1_floor() -> None:
    report = run_rules_vs_labels()
    assert report["n"] == 40
    for field in ("urgency", "category", "sentiment"):
        assert "hits" in report["fields"][field]
    assert report["macro_f1"] >= MACRO_F1_FLOOR, format_hit_report(report)


def test_under_threshold_macro_f1_fails_gate() -> None:
    """Fixture below MACRO_F1_FLOOR must fail the CI inequality."""
    gold = [{"urgency": "high", "category": "incident", "sentiment": "negative"}] * 4
    pred = [{"urgency": "low", "category": "other", "sentiment": "positive"}] * 4
    report = score_triage_fields(gold, pred)
    assert report["macro_f1"] < MACRO_F1_FLOOR
