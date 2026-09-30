"""Exact unit tests for triage scorers (P4)."""

from __future__ import annotations

from opspilot.evals.scorer import f1_for_labels, score_triage_fields, validity_rate


def test_f1_perfect() -> None:
    assert f1_for_labels(["a", "b", "a"], ["a", "b", "a"]) == 1.0


def test_f1_all_wrong_two_class() -> None:
    # Swapped labels → F1 0 for each class in binary swap of equal counts
    score = f1_for_labels(["a", "a", "b", "b"], ["b", "b", "a", "a"])
    assert score == 0.0


def test_score_triage_fields_hits() -> None:
    gold = [
        {"urgency": "low", "category": "other", "sentiment": "neutral"},
        {"urgency": "high", "category": "incident", "sentiment": "negative"},
    ]
    pred = [
        {"urgency": "low", "category": "other", "sentiment": "positive"},
        {"urgency": "high", "category": "request", "sentiment": "negative"},
    ]
    report = score_triage_fields(gold, pred)
    assert report["n"] == 2
    assert report["fields"]["urgency"]["hits"] == 2
    assert report["fields"]["category"]["hits"] == 1
    assert report["fields"]["sentiment"]["hits"] == 1
    assert 0.0 <= report["macro_f1"] <= 1.0


def test_validity_rate() -> None:
    assert validity_rate(accepted=8, attempts=10) == 0.8
    assert validity_rate(accepted=0, attempts=0) == 0.0
