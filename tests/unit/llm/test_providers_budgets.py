"""Hermetic provider + budget + routing tests (MockTransport)."""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from opspilot.llm.budgets import try_consume_request, utc_budget_day
from opspilot.llm.circuit import CircuitBreaker
from opspilot.llm.providers.gemini import GeminiProvider
from opspilot.llm.providers.openai_compatible import OpenAICompatibleProvider
from opspilot.llm.routed import BudgetAwareGateway
from opspilot.llm.routing import provider_order
from opspilot.llm.types import AttemptStatus, Message, ProviderResult
from opspilot.persistence.models import LlmBudgetCounterRow


@pytest.fixture()
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)


def test_provider_order_excludes_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INFERENCE_PROVIDER_ORDER", "gemini,anthropic,groq")
    assert provider_order() == ["gemini", "groq"]


def test_gemini_success_with_mock_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "generativelanguage.googleapis.com" in str(request.url)
        assert request.url.params.get("key") == "test-key"
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "hello gemini"}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2},
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = GeminiProvider(client=client)
    result = provider.complete(task="ask", messages=[Message(role="user", content="hi")], max_tokens=64)
    assert result.status is AttemptStatus.SUCCESS
    assert result.text == "hello gemini"
    client.close()


def test_gemini_429_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "1.5"}, json={"error": "rate"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = GeminiProvider(client=client).complete(
        task="ask", messages=[Message(role="user", content="hi")], max_tokens=16
    )
    assert result.status is AttemptStatus.RATE_LIMITED
    assert result.retry_after_s == 1.5
    client.close()


def test_groq_openai_compatible_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-8b-instant")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "api.groq.com" in str(request.url)
        body = json.loads(request.content.decode())
        assert body["model"] == "llama-3.1-8b-instant"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "groq ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = OpenAICompatibleProvider("groq", client=client).complete(
        task="ask", messages=[Message(role="user", content="hi")], max_tokens=32
    )
    assert result.status is AttemptStatus.SUCCESS
    assert result.text == "groq ok"
    client.close()


@pytest.mark.usefixtures("allow_llm")
def test_budget_aware_failover_on_429(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "10")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_REQ_DAY", "10")
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_TOK_DAY", "100000")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("GROQ_API_KEY", "gsk")
    day = utc_budget_day()
    db_session.execute(text("DELETE FROM llm_budget_counters WHERE day_utc = :d"), {"d": day})
    db_session.commit()

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host or ""
        calls.append(host)
        if "generativelanguage" in host:
            return httpx.Response(429, headers={"Retry-After": "0.01"}, json={})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "from groq"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    providers = [
        GeminiProvider(client=client),
        OpenAICompatibleProvider("groq", client=client),
    ]
    gw = BudgetAwareGateway(providers, session=db_session, observe=False, honor_retry_after=True)
    result = gw.complete(task="ask", messages=[Message(role="user", content="x")])
    assert result.provider == "groq"
    assert result.text == "from groq"
    assert any("generativelanguage" in h for h in calls)
    client.close()


def test_try_consume_respects_cap(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "2")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "1000")
    day = utc_budget_day()
    db_session.execute(
        text("DELETE FROM llm_budget_counters WHERE provider = :p AND day_utc = :d"),
        {"p": "gemini", "d": day},
    )
    db_session.commit()
    assert try_consume_request(db_session, provider="gemini") is True
    assert try_consume_request(db_session, provider="gemini") is True
    assert try_consume_request(db_session, provider="gemini") is False
    db_session.commit()
    row = db_session.get(LlmBudgetCounterRow, {"provider": "gemini", "day_utc": day})
    assert row is not None
    assert row.req_count == 2


def test_first_call_of_day_race(db_session: Session, monkeypatch: pytest.MonkeyPatch, test_database_url: str) -> None:
    """Two concurrent callers on empty day must not overspend req cap."""
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_REQ_DAY", "1")
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_TOK_DAY", "1000")
    day = utc_budget_day()
    # Ensure empty day
    db_session.execute(
        text("DELETE FROM llm_budget_counters WHERE provider = :p AND day_utc = :d"),
        {"p": "groq", "d": day},
    )
    db_session.commit()

    from opspilot.persistence.db import create_engine, create_session_factory

    engine = create_engine(test_database_url)
    factory = create_session_factory(engine)
    barrier = threading.Barrier(2)
    results: list[bool] = []

    def worker() -> None:
        session = factory()
        try:
            barrier.wait(timeout=5)
            ok = try_consume_request(session, provider="groq", day=day)
            session.commit()
            results.append(ok)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: worker(), range(2)))

    assert sorted(results) == [False, True]
    check = factory()
    try:
        row = check.execute(
            select(LlmBudgetCounterRow).where(
                LlmBudgetCounterRow.provider == "groq",
                LlmBudgetCounterRow.day_utc == day,
            )
        ).scalar_one()
        assert row.req_count == 1
    finally:
        check.close()
        engine.dispose()


def test_circuit_opens_after_error() -> None:
    circuit = CircuitBreaker(open_seconds=60)
    circuit.trip("gemini")
    assert circuit.is_open("gemini") is True
    circuit.reset("gemini")
    assert circuit.is_open("gemini") is False


def test_unset_budget_denies(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", raising=False)
    assert try_consume_request(db_session, provider="gemini") is False


def test_mistral_host_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MISTRAL_API_KEY", "mistral-test")
    monkeypatch.setenv("MISTRAL_MODEL", "mistral-small-latest")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "api.mistral.ai" in str(request.url)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = OpenAICompatibleProvider("mistral", client=client).complete(
        task="ask", messages=[Message(role="user", content="hi")], max_tokens=32
    )
    assert result.status is AttemptStatus.SUCCESS
    client.close()


def test_openrouter_host_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/auto")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "openrouter.ai" in str(request.url)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = OpenAICompatibleProvider("openrouter", client=client).complete(
        task="ask", messages=[Message(role="user", content="hi")], max_tokens=32
    )
    assert result.status is AttemptStatus.SUCCESS
    client.close()


def test_cloudflare_host_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "cf-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct-xyz")
    monkeypatch.setenv("CLOUDFLARE_MODEL", "@cf/meta/llama-3.1-8b-instruct")

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        assert "api.cloudflare.com" in url
        assert "acct-xyz" in url
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = OpenAICompatibleProvider("cloudflare", client=client).complete(
        task="ask", messages=[Message(role="user", content="hi")], max_tokens=32
    )
    assert result.status is AttemptStatus.SUCCESS
    client.close()


def test_ollama_host_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "127.0.0.1:11434" in str(request.url)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = OpenAICompatibleProvider("ollama", client=client).complete(
        task="ask", messages=[Message(role="user", content="hi")], max_tokens=32
    )
    assert result.status is AttemptStatus.SUCCESS
    client.close()


@pytest.mark.usefixtures("allow_llm")
def test_timeout_trips_circuit_and_skips_provider(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "20")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_REQ_DAY", "20")
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_TOK_DAY", "100000")
    from opspilot.llm.providers.fake import FakeProvider

    slow = FakeProvider(
        name="gemini",
        complete_results=[ProviderResult(status=AttemptStatus.TIMEOUT, error_code="timeout", model="g")],
    )
    fast = FakeProvider(name="groq", text_responder=lambda _t, _m: "recovered")
    circuit = CircuitBreaker(open_seconds=60)
    gw = BudgetAwareGateway([slow, fast], session=db_session, circuit=circuit, observe=False)
    first = gw.complete(task="ask", messages=[Message(role="user", content="a")])
    assert first.provider == "groq"
    assert first.text == "recovered"
    assert circuit.is_open("gemini") is True
    groq_calls = {"n": 0}
    orig = fast.complete

    def counting_complete(**kwargs):  # type: ignore[no-untyped-def]
        groq_calls["n"] += 1
        return orig(**kwargs)

    fast.complete = counting_complete  # type: ignore[method-assign]
    second = gw.complete(task="ask", messages=[Message(role="user", content="b")])
    assert second.provider == "groq"
    assert groq_calls["n"] == 1
