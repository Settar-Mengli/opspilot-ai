"""Fail-closed budgets on ask/evening/insights/triage/briefing; no bare LlmGateway outside llm/."""

from __future__ import annotations

import ast
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session

from opspilot.adapters.briefing_adapter import generate_ai_briefing
from opspilot.adapters.gateway_triage import GatewayTriageAdapter
from opspilot.llm.errors import LlmProvidersExhausted
from opspilot.llm.providers.fake import FakeProvider
from opspilot.llm.routed import BudgetAwareGateway
from opspilot.llm.types import AttemptStatus, Message, ProviderResult
from opspilot.models.schemas import WorkItem
from opspilot.services.ask import answer_question
from opspilot.services.evening import generate_evening_summary
from opspilot.services.insights import generate_insights


@pytest.fixture()
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)


@pytest.fixture()
def gemini_key_no_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("INFERENCE_PROVIDER_ORDER", "gemini")
    monkeypatch.delenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", raising=False)
    monkeypatch.delenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", raising=False)
    for name in (
        "GROQ_API_KEY",
        "MISTRAL_API_KEY",
        "OPENROUTER_API_KEY",
        "CLOUDFLARE_API_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)


def test_no_session_denies_without_calling_provider(allow_llm: None) -> None:
    hit = {"n": 0}

    def complete(**_kwargs):  # type: ignore[no-untyped-def]
        hit["n"] += 1
        return ProviderResult(status=AttemptStatus.SUCCESS, model="x", text="nope")

    fake = FakeProvider()
    fake.complete = complete  # type: ignore[method-assign]
    gw = BudgetAwareGateway([fake], session=None, observe=False)
    with pytest.raises(LlmProvidersExhausted, match="budget_denied_no_session"):
        gw.complete(task="ask", messages=[Message(role="user", content="hi")])
    assert hit["n"] == 0


@pytest.mark.usefixtures("allow_llm", "gemini_key_no_budget")
def test_unset_budget_soft_paths_never_hit_http(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    hits: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hits.append(str(request.url))
        return httpx.Response(500, json={"error": "should not be called"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    from opspilot.llm.providers import gemini as gemini_mod
    from opspilot.llm.routing import build_providers

    def _build(*_a, **_k):  # type: ignore[no-untyped-def]
        return [gemini_mod.GeminiProvider(api_key="fake-key", client=client)]

    monkeypatch.setattr("opspilot.services._llm.build_providers", _build)
    monkeypatch.setattr("opspilot.adapters.gateway_triage.build_providers", _build)
    monkeypatch.setattr("opspilot.llm.routing.build_providers", _build)

    ask = answer_question("What needs attention?", session=db_session)
    evening = generate_evening_summary(session=db_session)
    insights = generate_insights(session=db_session)
    item = WorkItem(
        id="wi-1",
        source_type="email",
        subject_or_title="Test",
        body_or_description="Body",
        sender_or_requester="a@example.com",
        received_at="2026-09-29T12:00:00Z",
        tags=[],
    )
    triage = GatewayTriageAdapter(session=db_session).classify(item)
    briefing = generate_ai_briefing("2026-09-29", [], [], [], "fallback template", session=db_session)

    assert hits == []
    assert "unavailable" in ask.lower() or "API" in ask or "moment" in ask.lower()
    assert evening  # soft string
    assert insights["insights"] == []
    assert triage.urgency  # rules fallback still classifies
    assert briefing == "fallback template"
    client.close()
    _ = build_providers  # keep import used for patch targets clarity


def test_no_bare_llm_gateway_outside_llm_package() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "opspilot"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if "llm" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "opspilot.llm.gateway" or node.module.startswith("opspilot.llm.gateway"):
                    for alias in node.names:
                        if alias.name in {"LlmGateway", "complete", "complete_json", "stream"}:
                            offenders.append(f"{path.relative_to(root.parent.parent)}:{node.lineno}:{alias.name}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "opspilot.llm.gateway":
                        offenders.append(f"{path.relative_to(root.parent.parent)}:{node.lineno}:import")
    assert offenders == [], f"bare LlmGateway usage outside llm/: {offenders}"
