"""Grounding helper unit tests (P12)."""

from __future__ import annotations

import pytest

from opspilot.llm.grounding import GroundingError, assert_grounded
from opspilot.llm.schemas.triage import TriagePayload


def _payload(**kwargs: object) -> TriagePayload:
    base = {
        "urgency": "low",
        "urgency_reason": "routine",
        "category": "other",
        "category_reason": "misc",
        "sentiment": "neutral",
        "sentiment_reason": "flat",
        "confidence": 0.5,
        "evidence_refs": ["wi-1"],
    }
    base.update(kwargs)
    return TriagePayload.model_validate(base)


def test_assert_grounded_ok() -> None:
    assert_grounded(_payload(), allowed_ids={"wi-1"})


def test_assert_grounded_rejects_extra_ref() -> None:
    with pytest.raises(GroundingError):
        assert_grounded(_payload(evidence_refs=["wi-1", "evil"]), allowed_ids={"wi-1"})


def test_assert_grounded_rejects_marker_leak() -> None:
    with pytest.raises(GroundingError):
        assert_grounded(_payload(urgency_reason="see <<<UNTRUSTED"), allowed_ids={"wi-1"})
