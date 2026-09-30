"""Rules-vs-labels hermetic eval runner (P4)."""

from __future__ import annotations

from typing import Any

from opspilot.evals.dataset import case_to_work_item, load_triage_cases
from opspilot.evals.scorer import confusion_matrix, score_triage_fields
from opspilot.rules.triage_rules import classify_work_item

# Owner-locked at STOP F1-FLOOR (measured macro-F1 ≈ 0.3256 on C6).
MACRO_F1_FLOOR = 0.30


def run_rules_vs_labels() -> dict[str, Any]:
    cases = load_triage_cases()
    gold: list[dict[str, str]] = []
    pred: list[dict[str, str]] = []
    for case in cases:
        labels = case["labels"]
        gold.append(
            {
                "urgency": str(labels["urgency"]),
                "category": str(labels["category"]),
                "sentiment": str(labels["sentiment"]),
            }
        )
        record = classify_work_item(case_to_work_item(case))
        pred.append(
            {
                "urgency": record.urgency,
                "category": record.category,
                "sentiment": record.sentiment,
            }
        )
    report = score_triage_fields(gold, pred)
    report["confusion"] = {
        field: confusion_matrix([g[field] for g in gold], [p[field] for p in pred])
        for field in ("urgency", "category", "sentiment")
    }
    return report


def format_hit_report(report: dict[str, Any]) -> str:
    lines = [f"n={report['n']} macro_f1={report['macro_f1']:.4f}"]
    for field, stats in report["fields"].items():
        lines.append(f"  {field}: hits={stats['hits']}/{stats['n']} f1={stats['f1']:.4f}")
    return "\n".join(lines)
