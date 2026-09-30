"""Timestamp tests: pace every structured HTTP attempt (D-LIVE-7)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from opspilot.llm.providers.fake import FakeProvider
from opspilot.llm.routed import BudgetAwareGateway
from opspilot.llm.schemas.triage import TriagePayload
from opspilot.llm.types import Message, TaskName


@pytest.fixture
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)


def _payload(item_id: str = "x") -> str:
    return json.dumps(
        {
            "urgency": "low",
            "urgency_reason": "ok",
            "category": "other",
            "category_reason": "ok",
            "sentiment": "neutral",
            "sentiment_reason": "ok",
            "confidence": 0.5,
            "evidence_refs": [item_id],
        }
    )


@pytest.mark.usefixtures("allow_llm")
def test_request_pacer_runs_before_each_structured_http(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "50")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")

    pace_times: list[float] = []
    mono = {"t": 1000.0}

    def fake_mono() -> float:
        return mono["t"]

    def pacer() -> None:
        pace_times.append(fake_mono())
        mono["t"] += 0.01  # simulate time advancing after wait

    calls = {"n": 0}

    def responder(
        task: TaskName,
        messages: list[Message],
        schema: type[TriagePayload],
        repair_hint: str | None,
    ) -> str:
        del task, messages, schema
        calls["n"] += 1
        mono["t"] += 0.05  # provider latency
        if repair_hint is None and calls["n"] == 1:
            return "{}"
        return _payload("x")

    gw = BudgetAwareGateway(
        [FakeProvider(name="gemini", json_responder=responder)],  # type: ignore[arg-type]
        session=db_session,
        observe=False,
        request_pacer=pacer,
    )
    out = gw.complete_json(
        task="triage",
        messages=[Message(role="user", content="x")],
        schema=TriagePayload,
        max_tokens=1024,
    )
    assert out.urgency == "low"
    # Initial attempt + repair attempt each paced once.
    assert len(pace_times) == 2
    assert pace_times[1] > pace_times[0]
    assert gw.last_repair_used is True
