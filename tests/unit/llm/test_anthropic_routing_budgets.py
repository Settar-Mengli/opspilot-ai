"""Budgets + routing Anthropic branch (A5/L6)."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from opspilot.llm.budgets import add_tokens, tokens_exhausted, try_consume_request
from opspilot.llm.operator_auth import OperatorAnthropicAuth
from opspilot.llm.routing import build_providers, provider_order
from opspilot.persistence.models import LlmBudgetCounterRow


def test_anthropic_skips_daily_counter(db_session: Session) -> None:
    assert try_consume_request(db_session, provider="anthropic") is True
    assert tokens_exhausted(db_session, provider="anthropic") is False
    rows = db_session.scalars(select(LlmBudgetCounterRow)).all()
    assert rows == []


def test_add_tokens_noop_for_anthropic(db_session: Session) -> None:
    add_tokens(db_session, provider="anthropic", tokens=999)
    rows = db_session.scalars(select(LlmBudgetCounterRow)).all()
    assert rows == []


def test_unknown_provider_still_fail_closed(db_session: Session) -> None:
    assert try_consume_request(db_session, provider="not_a_real_provider") is False
    assert tokens_exhausted(db_session, provider="not_a_real_provider") is True


def test_routing_strips_anthropic_from_env_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INFERENCE_PROVIDER_ORDER", "gemini,anthropic,groq")
    assert "anthropic" not in provider_order()


def test_routing_prepends_when_authorized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    auth = OperatorAnthropicAuth(role="demo_operator")
    providers = build_providers(order=["fake"], operator_auth=auth, session=None, task="ask")
    assert providers[0].name == "anthropic"
    assert any(p.name == "fake" for p in providers)


def test_routing_flag_off_no_anthropic_even_with_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "0")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    auth = OperatorAnthropicAuth(role="demo_operator")
    providers = build_providers(order=["fake"], operator_auth=auth, session=None, task="ask")
    assert all(p.name != "anthropic" for p in providers)
    assert any(p.name == "fake" for p in providers)


def test_routing_no_task_no_anthropic_even_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    auth = OperatorAnthropicAuth(role="demo_operator")
    providers = build_providers(order=["fake"], operator_auth=auth, session=None, task=None)
    assert all(p.name != "anthropic" for p in providers)
