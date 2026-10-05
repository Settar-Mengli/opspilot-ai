"""complete_structured soft paths unchanged; complete_structured_raising re-raises budget/exhaustion."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from opspilot.llm.errors import LlmPolicyDenied, LlmProvidersExhausted


class _Dummy(BaseModel):
    answer: str


def test_complete_structured_returns_none_on_exhaustion(monkeypatch: pytest.MonkeyPatch) -> None:
    """complete_structured swallows LlmProvidersExhausted → None."""
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "0")

    from opspilot.services._llm import complete_structured

    # No providers → None (never raises).
    monkeypatch.setattr("opspilot.services._llm.providers_or_empty", lambda: [])
    result = complete_structured(
        task="triage",
        system="sys",
        user="u",
        schema=_Dummy,
        max_tokens=100,
    )
    assert result is None


def test_complete_structured_raising_raises_policy_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    """complete_structured_raising propagates LlmPolicyDenied."""
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")

    from opspilot.services._llm import complete_structured_raising

    with pytest.raises(LlmPolicyDenied):
        complete_structured_raising(
            task="triage",
            system="sys",
            user="u",
            schema=_Dummy,
            max_tokens=100,
            session=None,  # type: ignore[arg-type]
        )


def test_complete_structured_raising_raises_no_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    """complete_structured_raising propagates LlmProvidersExhausted when no providers."""
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "0")

    from opspilot.services._llm import complete_structured_raising

    monkeypatch.setattr("opspilot.services._llm.providers_or_empty", lambda: [])
    with pytest.raises(LlmProvidersExhausted, match="no_providers"):
        complete_structured_raising(
            task="triage",
            system="sys",
            user="u",
            schema=_Dummy,
            max_tokens=100,
            session=None,  # type: ignore[arg-type]
        )


def test_gateway_triage_uses_rules_on_soft_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """GatewayTriageAdapter falls back to rules (soft) — complete_structured returns None."""
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")

    from opspilot.adapters.gateway_triage import GatewayTriageAdapter
    from opspilot.models.schemas import WorkItem

    adapter = GatewayTriageAdapter()
    item = WorkItem(
        id="wi_test",
        source_type="gmail",
        subject_or_title="Server down!",
        body_or_description="Our server is down and customers are complaining.",
        sender_or_requester="ops@example.com",
        received_at="2026-10-03T08:00:00Z",
        tags=[],
    )
    result = adapter.classify(item)
    assert result.urgency in {"critical", "high", "medium", "low"}
    assert result.id == "wi_test"
