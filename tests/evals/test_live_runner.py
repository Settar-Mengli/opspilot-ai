"""FakeProvider unit tests for single-provider live eval wiring (C10)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from opspilot.evals.live import LiveEvalError, resolve_single_provider, run_live
from opspilot.jobs.run_evals import main
from opspilot.llm.providers.fake import FakeProvider
from opspilot.llm.schemas.triage import TriagePayload
from opspilot.llm.types import Message, TaskName


@pytest.fixture
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)


def _valid_payload(item_id: str, *, urgency: str = "low") -> str:
    return json.dumps(
        {
            "urgency": urgency,
            "urgency_reason": "unit test reason",
            "category": "other",
            "category_reason": "unit test reason",
            "sentiment": "neutral",
            "sentiment_reason": "unit test reason",
            "confidence": 0.5,
            "evidence_refs": [item_id],
        }
    )


@pytest.mark.usefixtures("allow_llm")
def test_resolve_refuses_anthropic() -> None:
    with pytest.raises(LiveEvalError, match="Anthropic"):
        resolve_single_provider("anthropic")


@pytest.mark.usefixtures("allow_llm")
def test_resolve_single_injected_provider() -> None:
    fake = FakeProvider(name="gemini")
    out = resolve_single_provider("gemini", providers=[fake])
    assert len(out) == 1
    assert out[0].name == "gemini"


@pytest.mark.usefixtures("allow_llm")
def test_live_runner_fake_provider_metrics(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "200")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "500000")

    calls = {"n": 0}

    def responder(
        task: TaskName,
        messages: list[Message],
        schema: type[TriagePayload],
        repair_hint: str | None,
    ) -> str:
        del task, schema
        calls["n"] += 1
        # First triage attempt returns invalid JSON to exercise repair path.
        if repair_hint is None and calls["n"] == 1:
            return "{}"
        # Extract id from wrapped user message for evidence_refs.
        user = messages[-1].content if messages else ""
        item_id = "triage-v1-001"
        if 'id="' in user:
            item_id = user.split('id="', 1)[1].split('"', 1)[0]
        return _valid_payload(item_id)

    fake = FakeProvider(name="gemini", json_responder=responder)  # type: ignore[arg-type]
    report = run_live(
        provider_name="gemini",
        session=db_session,
        providers=[fake],
        triage_limit=2,
        redteam_limit=1,
    )
    assert report["mode"] == "live"
    assert report["provider"] == "gemini"
    assert report["anthropic"] == "skipped"
    assert report["attempts"] == 3
    assert report["accepted"] >= 1
    assert 0.0 <= report["validity_pct"] <= 1.0
    assert report["repair_events"] >= 1
    assert "p50" in report["latency_ms"]
    assert "rate" in report["asr"]


def test_cli_live_requires_provider() -> None:
    assert main(["--live"]) == 2


def test_cli_live_refuses_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    assert main(["--live", "--provider", "anthropic"]) == 2
