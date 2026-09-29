"""Unit tests for C2 LLM gateway skeleton (fake provider only)."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field

from opspilot.llm import (
    FakeProvider,
    LlmGateway,
    LlmPolicyDenied,
    LlmProvidersExhausted,
    LlmSchemaError,
    Message,
)
from opspilot.llm.types import AttemptStatus, ProviderResult


@pytest.fixture()
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gateway happy-path tests need remote policy open; fake stays hermetic."""
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)


class _InsightOut(BaseModel):
    title: str
    detail: str = Field(min_length=1)


@pytest.mark.usefixtures("allow_llm")
def test_complete_returns_fake_text() -> None:
    gw = LlmGateway([FakeProvider(text_responder=lambda task, msgs: f"ok:{task}")], observe=False)
    result = gw.complete(task="ask", messages=[Message(role="user", content="hello")])
    assert result.provider == "fake"
    assert result.text == "ok:ask"
    assert result.model == "fake-v1"


@pytest.mark.usefixtures("allow_llm")
def test_complete_fails_over_to_second_provider() -> None:
    failing = FakeProvider(
        name="bad",
        complete_results=[
            ProviderResult(status=AttemptStatus.ERROR, error_code="boom", model="bad-v1"),
        ],
    )
    ok = FakeProvider(name="good", text_responder=lambda _t, _m: "recovered")
    gw = LlmGateway([failing, ok], observe=False)
    result = gw.complete(task="ask", messages=[Message(role="user", content="x")])
    assert result.provider == "good"
    assert result.text == "recovered"


@pytest.mark.usefixtures("allow_llm")
def test_complete_exhausted_raises() -> None:
    bad = FakeProvider(
        complete_results=[ProviderResult(status=AttemptStatus.TIMEOUT, error_code="timeout")],
    )
    gw = LlmGateway([bad], observe=False)
    with pytest.raises(LlmProvidersExhausted):
        gw.complete(task="ask", messages=[Message(role="user", content="x")])


@pytest.mark.usefixtures("allow_llm")
def test_complete_json_validates_schema() -> None:
    def _respond(_task, _msgs, _schema, _hint):  # type: ignore[no-untyped-def]
        return json.dumps({"title": "A", "detail": "B"})

    gw = LlmGateway([FakeProvider(json_responder=_respond)], observe=False)
    out = gw.complete_json(
        task="insights",
        messages=[Message(role="user", content="summarize")],
        schema=_InsightOut,
    )
    assert out.title == "A"
    assert out.detail == "B"


@pytest.mark.usefixtures("allow_llm")
def test_complete_json_repairs_once_then_succeeds() -> None:
    calls: list[str | None] = []

    def _respond(_task, _msgs, _schema, hint):  # type: ignore[no-untyped-def]
        calls.append(hint)
        if hint is None:
            return '{"title": 1}'
        return json.dumps({"title": "fixed", "detail": "ok"})

    gw = LlmGateway([FakeProvider(json_responder=_respond)], observe=False)
    out = gw.complete_json(
        task="insights",
        messages=[Message(role="user", content="x")],
        schema=_InsightOut,
    )
    assert out.title == "fixed"
    assert len(calls) == 2
    assert calls[0] is None
    assert calls[1] is not None


@pytest.mark.usefixtures("allow_llm")
def test_complete_json_fails_after_one_repair() -> None:
    def _respond(_task, _msgs, _schema, _hint):  # type: ignore[no-untyped-def]
        return '{"title": 1}'

    gw = LlmGateway([FakeProvider(json_responder=_respond)], observe=False)
    with pytest.raises(LlmSchemaError):
        gw.complete_json(
            task="insights",
            messages=[Message(role="user", content="x")],
            schema=_InsightOut,
        )


@pytest.mark.usefixtures("allow_llm")
def test_stream_yields_chunks() -> None:
    gw = LlmGateway([FakeProvider(stream_chunks=["hel", "lo"])], observe=False)
    chunks = list(gw.stream(task="ask", messages=[Message(role="user", content="hi")]))
    assert "".join(c.text for c in chunks) == "hello"
    assert chunks[-1].done is True
    assert all(c.provider == "fake" for c in chunks)


def test_policy_denied_without_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    gw = LlmGateway([FakeProvider()])
    with pytest.raises(LlmPolicyDenied):
        gw.complete(task="ask", messages=[Message(role="user", content="x")])


def test_gateway_requires_provider() -> None:
    with pytest.raises(ValueError):
        LlmGateway([])
