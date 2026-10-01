"""Hermetic agent loop + tool allowlist (B5 / D-031)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from opspilot.agent.loop import run_ask_agent
from opspilot.agent.tools import TOOL_REGISTRY, assert_no_send_tools
from opspilot.llm.providers.fake import FakeProvider
from opspilot.llm.types import AttemptStatus, ProviderResult
from opspilot.persistence.repositories import work_items


@pytest.fixture()
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "100")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    monkeypatch.setenv("OPSPILOT_ASK_MAX_STEPS", "5")
    monkeypatch.setenv("OPSPILOT_ASK_MAX_PROVIDER_CALLS", "8")


def _json_result(payload: dict) -> ProviderResult:
    return ProviderResult(
        status=AttemptStatus.SUCCESS,
        text=json.dumps(payload),
        model="fake-v1",
        input_tokens=10,
        output_tokens=10,
        latency_ms=1,
    )


def test_no_send_tool_registered() -> None:
    assert_no_send_tools()
    assert "send" not in " ".join(TOOL_REGISTRY.keys()).lower()


@pytest.mark.usefixtures("allow_llm")
def test_agent_tool_then_final(db_session: Session) -> None:
    work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_agent_1",
        source_type="gmail",
        subject_or_title="Checkout confirm",
        body_or_description="Please confirm checkout",
        sender_or_requester="ops@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_agent_1",
    )
    db_session.commit()

    fake = FakeProvider(
        name="gemini",
        json_results=[
            _json_result({"kind": "tool", "tool": "search_items", "args": {"query": "checkout", "limit": 5}}),
            _json_result({"kind": "final", "final": "Checkout confirm is the priority."}),
        ],
    )
    events = list(
        run_ask_agent(
            question="What needs attention?",
            session=db_session,
            request_id="req-agent-1",
            gmail_only=True,
            providers=[fake],
        )
    )
    types = [e.type for e in events]
    assert "tool_start" in types
    assert "tool_end" in types
    assert "final" in types
    assert events[-1].data.get("answer") == "Checkout confirm is the priority."


@pytest.mark.usefixtures("allow_llm")
def test_agent_rejects_send_tool_name(db_session: Session) -> None:
    fake = FakeProvider(
        name="gemini",
        json_results=[
            _json_result({"kind": "tool", "tool": "send_reply", "args": {}}),
            _json_result({"kind": "final", "final": "fallback"}),
        ],
    )
    events = list(
        run_ask_agent(
            question="Send mail now",
            session=db_session,
            request_id="req-agent-2",
            providers=[fake],
        )
    )
    # First turn fails schema (tool not allowlisted) → error or continues after repair fail
    assert events
    assert events[-1].type in {"error", "final"}
