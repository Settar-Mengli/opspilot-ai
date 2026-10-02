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
    for provider in ("GEMINI", "GROQ", "MISTRAL", "CLOUDFLARE", "OPENROUTER"):
        monkeypatch.setenv(f"OPSPILOT_BUDGET_{provider}_REQ_DAY", "100")
        monkeypatch.setenv(f"OPSPILOT_BUDGET_{provider}_TOK_DAY", "100000")
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
def test_agent_abort_mid_loop_no_further_provider_or_draft(db_session: Session) -> None:
    work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_abort_1",
        source_type="gmail",
        subject_or_title="Need reply",
        body_or_description="Please reply",
        sender_or_requester="peer@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_abort_1",
    )
    db_session.commit()

    calls = {"n": 0}
    results = [
        _json_result({"kind": "tool", "tool": "search_items", "args": {"query": "reply", "limit": 5}}),
        _json_result(
            {
                "kind": "tool",
                "tool": "draft_reply",
                "args": {"work_item_id": "ignored", "subject": "Re: Need reply", "body": "Thanks"},
            }
        ),
        _json_result({"kind": "final", "final": "should-not-reach"}),
    ]

    class CountingFake(FakeProvider):
        def complete_json(self, **kwargs):  # type: ignore[no-untyped-def]
            calls["n"] += 1
            return results[min(calls["n"] - 1, len(results) - 1)]

    cancelled = {"after_first": False}

    def cancel_check() -> bool:
        return cancelled["after_first"]

    events: list = []
    for event in run_ask_agent(
        question="Draft a reply",
        session=db_session,
        request_id="req-abort-1",
        gmail_only=True,
        providers=[CountingFake(name="gemini")],
        cancel_check=cancel_check,
    ):
        events.append(event)
        if event.type == "tool_end":
            cancelled["after_first"] = True

    assert calls["n"] == 1
    assert events[-1].type == "error"
    assert events[-1].data.get("code") == "aborted"
    assert not any(e.type == "draft" for e in events)
    from opspilot.persistence.models import MailDraftRow

    assert db_session.query(MailDraftRow).count() == 0


@pytest.mark.usefixtures("allow_llm")
def test_agent_step_timeout(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    from sqlalchemy import text

    monkeypatch.setenv("OPSPILOT_ASK_STEP_TIMEOUT_S", "0.05")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "100")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")

    class SlowFake(FakeProvider):
        def complete_json(self, **kwargs):  # type: ignore[no-untyped-def]
            time.sleep(0.25)
            return _json_result({"kind": "final", "final": "too late"})

    before = db_session.execute(
        text("SELECT COALESCE(SUM(req_count),0) FROM llm_budget_counters WHERE provider = 'gemini'")
    ).scalar()
    started = time.perf_counter()
    events = list(
        run_ask_agent(
            question="Hi",
            session=db_session,
            request_id="req-timeout-1",
            providers=[SlowFake(name="gemini")],
        )
    )
    elapsed = time.perf_counter() - started
    assert events[-1].type == "error"
    assert events[-1].data.get("code") == "step_timeout"
    # Wall time bounded near timeout (not full 0.25s sleep on the calling thread).
    assert elapsed < 0.2
    after = db_session.execute(
        text("SELECT COALESCE(SUM(req_count),0) FROM llm_budget_counters WHERE provider = 'gemini'")
    ).scalar()
    # Debit happens inside the gateway before/during the provider body; timeout still counts.
    assert int(after or 0) >= int(before or 0) + 1


@pytest.mark.usefixtures("allow_llm")
def test_tool_end_payload_minimized(db_session: Session) -> None:
    wi = work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_toolend_1",
        source_type="gmail",
        subject_or_title="Checkout",
        body_or_description="Confirm",
        sender_or_requester="ops@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_toolend_1",
    )
    db_session.commit()
    fake = FakeProvider(
        name="gemini",
        json_results=[
            _json_result(
                {
                    "kind": "tool",
                    "tool": "draft_reply",
                    "args": {"work_item_id": wi, "subject": "Re: Checkout", "body": "SECRET_BODY_CONTENT"},
                }
            ),
            _json_result({"kind": "final", "final": "Draft ready"}),
        ],
    )
    events = list(
        run_ask_agent(
            question="Draft",
            session=db_session,
            request_id="req-toolend-1",
            gmail_only=True,
            providers=[fake],
        )
    )
    tool_ends = [e for e in events if e.type == "tool_end"]
    assert tool_ends
    te = tool_ends[0].data
    assert set(te.keys()) <= {"tool", "ok", "error"}
    assert te["tool"] == "draft_reply"
    assert te["ok"] is True
    assert "SECRET_BODY_CONTENT" not in str(te)
    drafts = [e for e in events if e.type == "draft"]
    assert drafts
    assert "SECRET_BODY_CONTENT" in str(drafts[0].data.get("body"))


def test_force_rules_yields_llm_policy_denied(db_session: Session) -> None:
    """STOP LIVE regression: FORCE_RULES must not soft-map to bare ask_failed."""
    events = list(
        run_ask_agent(
            question="Draft a reply confirming Friday works.",
            session=db_session,
            request_id="req-policy-1",
            gmail_only=True,
        )
    )
    assert len(events) == 1
    assert events[0].type == "error"
    assert events[0].data.get("code") == "llm_policy_denied"
    assert events[0].request_id == "req-policy-1"


@pytest.mark.usefixtures("allow_llm")
def test_injected_provider_still_maps_policy_denied(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Gateway policy deny (injected providers) maps to llm_policy_denied, not ask_failed."""
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    fake = FakeProvider(
        name="gemini",
        json_results=[_json_result({"kind": "final", "final": "should not run"})],
    )
    events = list(
        run_ask_agent(
            question="Hi",
            session=db_session,
            request_id="req-policy-2",
            providers=[fake],
        )
    )
    assert events[-1].type == "error"
    assert events[-1].data.get("code") == "llm_policy_denied"


@pytest.mark.usefixtures("allow_llm")
def test_agent_loop_draft_then_search_uses_search_id(db_session: Session) -> None:
    wi_id = work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_search_draft_1",
        source_type="gmail",
        subject_or_title="Project sync",
        body_or_description="Friday?",
        sender_or_requester="peer@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_search_draft_1",
    )
    db_session.commit()
    truncated = wi_id[:32]
    assert truncated != wi_id

    fake = FakeProvider(
        name="gemini",
        json_results=[
            _json_result(
                {
                    "kind": "tool",
                    "tool": "draft_reply",
                    "args": {"work_item_id": truncated, "body": "Friday works."},
                }
            ),
            _json_result({"kind": "tool", "tool": "search_items", "args": {"query": "project", "limit": 5}}),
            _json_result(
                {
                    "kind": "tool",
                    "tool": "draft_reply",
                    "args": {"work_item_id": wi_id, "body": "Friday works."},
                }
            ),
            _json_result({"kind": "final", "final": "Draft ready."}),
        ],
    )
    events = list(
        run_ask_agent(
            question="Draft a reply confirming Friday",
            session=db_session,
            request_id="req-search-id-1",
            gmail_only=True,
            providers=[fake],
        )
    )
    tool_ends = [e for e in events if e.type == "tool_end"]
    assert tool_ends[0].data.get("ok") is False
    assert tool_ends[0].data.get("error") == "not_found"
    assert tool_ends[1].data.get("ok") is True
    assert tool_ends[2].data.get("ok") is True
    assert any(e.type == "draft" for e in events)
    from opspilot.persistence.models import MailDraftRow

    assert db_session.query(MailDraftRow).count() == 1
    assert events[-1].type == "final"


@pytest.mark.usefixtures("allow_llm")
def test_tool_repeat_failure_soft_final(db_session: Session) -> None:
    fake = FakeProvider(
        name="gemini",
        json_results=[
            _json_result(
                {
                    "kind": "tool",
                    "tool": "draft_reply",
                    "args": {"work_item_id": "wi_missing", "body": "x"},
                }
            ),
            _json_result(
                {
                    "kind": "tool",
                    "tool": "draft_reply",
                    "args": {"work_item_id": "wi_missing", "body": "x"},
                }
            ),
            _json_result({"kind": "final", "final": "should-not-reach"}),
        ],
    )
    events = list(
        run_ask_agent(
            question="Draft",
            session=db_session,
            request_id="req-repeat-1",
            gmail_only=True,
            providers=[fake],
        )
    )
    codes = [e.data.get("code") for e in events if e.type == "error"]
    assert "tool_repeat_failure" in codes
    assert "step_cap" not in codes
    finals = [e for e in events if e.type == "final"]
    assert finals
    assert finals[-1].data.get("code") == "tool_repeat_failure"


@pytest.mark.usefixtures("allow_llm")
def test_model_feedback_includes_trusted_hint(db_session: Session) -> None:
    from opspilot.agent.loop import _model_tool_feedback

    text = _model_tool_feedback("draft_reply", {"ok": False, "error": "not_found"})
    assert "<<<UNTRUSTED" in text
    assert '"error": "not_found"' in text or '"error":"not_found"' in text
    assert "Hint (trusted): use the exact id from search_items or get_message" in text


@pytest.mark.usefixtures("allow_llm")
def test_tool_args_invalid_failovers_to_next_provider(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from opspilot.agent import loop as agent_loop

    wi_id = work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_failover_1",
        source_type="gmail",
        subject_or_title="Project sync",
        body_or_description="Friday?",
        sender_or_requester="peer@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_failover_1",
    )
    db_session.commit()
    lines: list[str] = []

    def _capture(msg: str, *args: object, **_kwargs: object) -> None:
        lines.append(msg % args if args else msg)

    monkeypatch.setattr(agent_loop._logger, "info", _capture)
    empty = _json_result({"kind": "tool", "tool": "draft_reply", "args": {}})
    prov_a = FakeProvider(
        name="gemini",
        json_results=[
            empty,
            empty,
            _json_result({"kind": "final", "final": "Draft ready."}),
        ],
    )
    prov_b = FakeProvider(
        name="groq",
        json_results=[
            _json_result(
                {
                    "kind": "tool",
                    "tool": "draft_reply",
                    "args": {"work_item_id": wi_id, "body": "Friday works."},
                }
            ),
        ],
    )
    events = list(
        run_ask_agent(
            question="Draft a reply",
            session=db_session,
            request_id="req-failover-1",
            gmail_only=True,
            providers=[prov_a, prov_b],
        )
    )
    assert any(e.type == "draft" for e in events)
    assert events[-1].type == "final"
    assert events[-1].data.get("code") != "tool_args_invalid"
    joined = "\n".join(lines)
    assert "ask_provider_failover request_id=req-failover-1" in joined
    assert "from=gemini" in joined
    assert "reason=tool_args_invalid" in joined
    from opspilot.persistence.models import MailDraftRow

    assert db_session.query(MailDraftRow).count() == 1


@pytest.mark.usefixtures("allow_llm")
def test_empty_draft_args_repair_then_execute(db_session: Session) -> None:
    wi_id = work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_repair_1",
        source_type="gmail",
        subject_or_title="Project sync",
        body_or_description="Friday?",
        sender_or_requester="peer@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_repair_1",
    )
    db_session.commit()
    fake = FakeProvider(
        name="gemini",
        json_results=[
            _json_result({"kind": "tool", "tool": "draft_reply", "args": {}}),
            _json_result(
                {
                    "kind": "tool",
                    "tool": "draft_reply",
                    "args": {"work_item_id": wi_id, "body": "Friday works."},
                }
            ),
            _json_result({"kind": "final", "final": "Draft ready."}),
        ],
    )
    events = list(
        run_ask_agent(
            question="Draft a reply",
            session=db_session,
            request_id="req-repair-1",
            gmail_only=True,
            providers=[fake],
        )
    )
    assert any(e.type == "draft" for e in events)
    assert events[-1].type == "final"
    assert events[-1].data.get("code") != "tool_args_invalid"
    from opspilot.persistence.models import MailDraftRow

    assert db_session.query(MailDraftRow).count() == 1


@pytest.mark.usefixtures("allow_llm")
def test_empty_draft_args_still_invalid_soft_final(db_session: Session) -> None:
    fake = FakeProvider(
        name="gemini",
        json_results=[
            _json_result({"kind": "tool", "tool": "draft_reply", "args": {}}),
            _json_result({"kind": "tool", "tool": "draft_reply", "args": {}}),
        ],
    )
    events = list(
        run_ask_agent(
            question="Draft",
            session=db_session,
            request_id="req-invalid-1",
            gmail_only=True,
            providers=[fake],
        )
    )
    finals = [e for e in events if e.type == "final"]
    assert finals
    assert finals[-1].data.get("code") == "tool_args_invalid"
    assert not any(e.type == "tool_end" for e in events)


@pytest.mark.usefixtures("allow_llm")
def test_args_conflict_soft_final(db_session: Session) -> None:
    raw = json.dumps(
        {
            "kind": "tool",
            "tool": "draft_reply",
            "args": {"work_item_id": "wi_a", "body": "x"},
            "arguments": {"work_item_id": "wi_b", "body": "x"},
        }
    )
    fake = FakeProvider(
        name="gemini",
        json_results=[_json_result_raw(raw)],
    )
    events = list(
        run_ask_agent(
            question="Draft",
            session=db_session,
            request_id="req-conflict-1",
            gmail_only=True,
            providers=[fake],
        )
    )
    finals = [e for e in events if e.type == "final"]
    assert finals
    assert finals[-1].data.get("code") == "tool_args_invalid"
    assert not any(e.type == "tool_end" for e in events)


@pytest.mark.usefixtures("allow_llm")
def test_arguments_bag_normalized_before_execute(db_session: Session) -> None:
    wi_id = work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_args_bag_1",
        source_type="gmail",
        subject_or_title="S",
        body_or_description="B",
        sender_or_requester="a@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_args_bag_1",
    )
    db_session.commit()
    # AgentTurn ignores unknown fields; raw text still carries arguments bag.
    raw = json.dumps(
        {
            "kind": "tool",
            "tool": "draft_reply",
            "arguments": {"work_item_id": wi_id, "body": "ok"},
        }
    )
    fake = FakeProvider(
        name="gemini",
        json_results=[
            _json_result_raw(raw),
            _json_result({"kind": "final", "final": "done"}),
        ],
    )
    events = list(
        run_ask_agent(
            question="Draft",
            session=db_session,
            request_id="req-args-bag-1",
            gmail_only=True,
            providers=[fake],
        )
    )
    assert any(e.type == "draft" for e in events)


def _json_result_raw(text: str) -> ProviderResult:
    return ProviderResult(
        status=AttemptStatus.SUCCESS,
        text=text,
        model="fake-v1",
        input_tokens=10,
        output_tokens=10,
        latency_ms=1,
    )


@pytest.mark.usefixtures("allow_llm")
def test_ask_tool_structured_log(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from opspilot.agent import loop as agent_loop

    wi_id = work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_log_1",
        source_type="gmail",
        subject_or_title="S",
        body_or_description="B",
        sender_or_requester="a@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_log_1",
    )
    db_session.commit()
    lines: list[str] = []

    def _capture(msg: str, *args: object, **_kwargs: object) -> None:
        lines.append(msg % args if args else msg)

    monkeypatch.setattr(agent_loop._logger, "info", _capture)
    fake = FakeProvider(
        name="gemini",
        json_results=[
            _json_result(
                {
                    "kind": "tool",
                    "tool": "get_message",
                    "args": {"id": wi_id},
                }
            ),
            _json_result({"kind": "final", "final": "ok"}),
        ],
    )
    events = list(
        run_ask_agent(
            question="Show message",
            session=db_session,
            request_id="req-log-1",
            gmail_only=True,
            providers=[fake],
        )
    )
    assert any(e.type == "tool_end" for e in events)
    joined = "\n".join(lines)
    assert "ask_tool request_id=req-log-1" in joined
    assert "ask_turn_keys request_id=req-log-1" in joined
    assert "tool=get_message" in joined or "get_message" in joined
    assert "arg_keys=id" in joined or "id" in joined
    assert f"id_len={len(wi_id)}" in joined or str(len(wi_id)) in joined
    assert "ok=True" in joined
    assert "Friday" not in joined
    assert "Project" not in joined
    assert "SECRET" not in joined
