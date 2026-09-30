"""Loader tests for triage corpus v1."""

from __future__ import annotations

from opspilot.evals.dataset import case_to_work_item, load_triage_cases


def test_load_triage_v1_has_forty_cases() -> None:
    cases = load_triage_cases()
    assert len(cases) == 40
    ids = {c["id"] for c in cases}
    assert len(ids) == 40
    for case in cases:
        labels = case["labels"]
        assert set(labels) == {"urgency", "category", "sentiment"}
        assert case["id"] in case["allowed_evidence_ids"]
        item = case_to_work_item(case)
        assert item.id == case["id"]
