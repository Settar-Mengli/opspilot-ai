"""Deterministic triage label scorers (P2 / P4)."""

from __future__ import annotations

from typing import Any


def f1_for_labels(y_true: list[str], y_pred: list[str]) -> float:
    """Unweighted macro-F1 over the union of labels present in y_true or y_pred."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred length mismatch")
    if not y_true:
        return 0.0
    labels = sorted(set(y_true) | set(y_pred))
    scores: list[float] = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        if precision + recall == 0:
            scores.append(0.0)
        else:
            scores.append(2 * precision * recall / (precision + recall))
    return sum(scores) / len(scores) if scores else 0.0


def score_triage_fields(
    gold: list[dict[str, str]],
    pred: list[dict[str, str]],
) -> dict[str, Any]:
    """Per-field F1 + macro-F1 + hit counts for urgency/category/sentiment."""
    if len(gold) != len(pred):
        raise ValueError("gold and pred length mismatch")
    fields = ("urgency", "category", "sentiment")
    out: dict[str, Any] = {"n": len(gold), "fields": {}}
    f1s: list[float] = []
    for field in fields:
        y_true = [g[field] for g in gold]
        y_pred = [p[field] for p in pred]
        hits = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == p)
        field_f1 = f1_for_labels(y_true, y_pred)
        f1s.append(field_f1)
        out["fields"][field] = {"hits": hits, "n": len(gold), "f1": field_f1}
    out["macro_f1"] = sum(f1s) / len(f1s) if f1s else 0.0
    return out


def confusion_matrix(y_true: list[str], y_pred: list[str]) -> dict[str, dict[str, int]]:
    labels = sorted(set(y_true) | set(y_pred))
    matrix: dict[str, dict[str, int]] = {a: {b: 0 for b in labels} for a in labels}
    for t, p in zip(y_true, y_pred, strict=True):
        matrix[t][p] += 1
    return matrix


def validity_rate(*, accepted: int, attempts: int) -> float:
    if attempts <= 0:
        return 0.0
    return accepted / attempts
