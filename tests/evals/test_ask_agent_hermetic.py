"""Hermetic ask_agent + redteam_agent eval suites (B5 / C8 / D-034)."""

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
    assert len(load_ask_agent_cases()) == 7
    report = run_ask_agent_hermetic(db_session)
    assert report["gate_passed"] is True, report["results"]
    assert report["passed"] == report["n"] == 7


@pytest.mark.usefixtures("allow_llm")
def test_redteam_agent_hermetic_suite(db_session: Session) -> None:
    assert len(load_redteam_agent_cases()) == 10
    report = run_redteam_agent_hermetic(db_session)
    assert report["gate_passed"] is True, report["results"]
    assert report["passed"] == report["n"] == 10


@pytest.mark.usefixtures("allow_llm")
def test_redteam_mcp_fails_without_neutralization(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Honest proof: MCP marker/role cases fail when neutralize_text is identity."""

    def _identity(text: str) -> str:
        return text or ""

    monkeypatch.setattr("opspilot.llm.prompt_safety.neutralize_text", _identity)
    monkeypatch.setattr("opspilot.integrations.github_mcp.client.neutralize_text", _identity)
    monkeypatch.setattr("opspilot.agent.safety.neutralize_text", _identity)

    report = run_redteam_agent_hermetic(db_session)
    by_id = {r["id"]: r for r in report["results"]}
    # Cases whose expect requires neutralization of markers / role prefixes.
    must_fail = ("rta-v1-006", "rta-v1-007", "rta-v1-008", "rta-v1-009")
    for case_id in must_fail:
        assert by_id[case_id]["passed"] is False, (case_id, by_id[case_id])
        assert by_id[case_id]["failures"], case_id
    # Plain-instruction case does not rely on neutralize — still passes under FakeProvider.
    assert by_id["rta-v1-010"]["passed"] is True, by_id["rta-v1-010"]
