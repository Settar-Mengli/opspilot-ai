"""Hermetic ask_agent + redteam_agent eval suites (B5 / C8)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from opspilot.evals.ask_agent import run_ask_agent_hermetic, run_redteam_agent_hermetic
from opspilot.evals.dataset import load_ask_agent_cases, load_redteam_agent_cases


@pytest.fixture()
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "100")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    monkeypatch.setenv("OPSPILOT_ASK_MAX_STEPS", "5")
    monkeypatch.setenv("OPSPILOT_ASK_MAX_PROVIDER_CALLS", "8")


@pytest.mark.usefixtures("allow_llm")
def test_ask_agent_hermetic_suite(db_session: Session) -> None:
    assert len(load_ask_agent_cases()) == 6
    report = run_ask_agent_hermetic(db_session)
    assert report["gate_passed"] is True, report["results"]
    assert report["passed"] == report["n"] == 6


@pytest.mark.usefixtures("allow_llm")
def test_redteam_agent_hermetic_suite(db_session: Session) -> None:
    assert len(load_redteam_agent_cases()) == 5
    report = run_redteam_agent_hermetic(db_session)
    assert report["gate_passed"] is True, report["results"]
    assert report["passed"] == report["n"] == 5
