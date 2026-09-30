"""Deterministic triage grounding checks (P12)."""

from __future__ import annotations

from collections.abc import Collection

from opspilot.llm.prompt_safety import reasons_leak_markers
from opspilot.llm.schemas.triage import TriagePayload


class GroundingError(ValueError):
    """Raised when evidence_refs escape the allowed id set or reasons leak markers."""


def assert_grounded(
    payload: TriagePayload,
    *,
    allowed_ids: Collection[str],
) -> None:
    """Fail closed if evidence_refs not ⊆ allowed_ids or reasons leak UNTRUSTED markers."""
    allowed = set(allowed_ids)
    refs = list(payload.evidence_refs)
    extra = [r for r in refs if r not in allowed]
    if extra:
        raise GroundingError(f"evidence_refs outside allowed ids: {extra}")
    if reasons_leak_markers(
        payload.urgency_reason,
        payload.category_reason,
        payload.sentiment_reason,
    ):
        raise GroundingError("reason fields leak UNTRUSTED/delimiter markers")
