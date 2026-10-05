"""Ask Anthropic operator wiring (C5) — hermetic; no live HTTP."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.api.app import app
from opspilot.api.deps import get_db_session, reset_db_engine
from opspilot.llm.providers.fake import FakeProvider
from opspilot.llm.types import AttemptStatus, ProviderResult
from opspilot.persistence.models import LlmCallRow
from opspilot.services.operator_session import COOKIE_NAME


@pytest.fixture()
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "100")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    monkeypatch.setenv("OPSPILOT_ASK_MAX_STEPS", "5")
    monkeypatch.setenv("OPSPILOT_ASK_MAX_PROVIDER_CALLS", "8")


@pytest.fixture()
def api_client(
    test_database_url: str, db_session: Session, monkeypatch: pytest.MonkeyPatch, allow_llm: None
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "c5-ask-wire-secret")
    monkeypatch.setenv("OPSPILOT_CSRF_RELAX_DEV", "1")
    reset_db_engine()

    def _override() -> Iterator[Session]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db_session] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    reset_db_engine()


def _anthropic_rows(session: Session) -> int:
    return int(
        session.scalar(select(func.count()).select_from(LlmCallRow).where(LlmCallRow.provider == "anthropic")) or 0
    )


def test_ask_stream_no_cookie_zero_anthropic_rows(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeProvider(
        name="gemini",
        json_results=[
            ProviderResult(
                status=AttemptStatus.SUCCESS,
                text=json.dumps({"kind": "final", "final": "free path"}),
                model="fake-v1",
            )
        ],
    )
    monkeypatch.setattr("opspilot.agent.loop.build_providers", lambda: [fake])
    before = _anthropic_rows(db_session)
    resp = api_client.post("/api/v1/ask/stream", json={"question": "Hi", "assistant_name": "OpsPilot"})
    assert resp.status_code == 200
    assert "free path" in resp.text
    assert _anthropic_rows(db_session) == before


def test_ask_stream_bad_cookie_zero_anthropic_rows(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeProvider(
        name="gemini",
        json_results=[
            ProviderResult(
                status=AttemptStatus.SUCCESS,
                text=json.dumps({"kind": "final", "final": "still free"}),
                model="fake-v1",
            )
        ],
    )
    monkeypatch.setattr("opspilot.agent.loop.build_providers", lambda: [fake])
    before = _anthropic_rows(db_session)
    resp = api_client.post(
        "/api/v1/ask/stream",
        json={"question": "Hi", "assistant_name": "OpsPilot"},
        cookies={COOKIE_NAME: "forged-not-a-real-session"},
    )
    assert resp.status_code == 200
    assert "still free" in resp.text
    assert _anthropic_rows(db_session) == before


@pytest.mark.usefixtures("allow_llm")
def test_ask_provider_calls_counts_anthropic_repairs_only(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each Anthropic HTTP attempt beyond the outer +1 bumps provider_calls (A5)."""
    from opspilot.agent.loop import run_ask_agent

    class _CountingAnth:
        name = "anthropic"
        anthropic_attempts = 0

        def complete_json(self, **_kwargs: Any) -> ProviderResult:
            self.anthropic_attempts += 3  # simulate initial + force_json + repair
            return ProviderResult(
                status=AttemptStatus.SUCCESS,
                text=json.dumps({"kind": "final", "final": "anth"}),
                model="claude-haiku-4-5-20251001",
            )

        def complete(self, **kwargs: Any) -> ProviderResult:
            return self.complete_json(**kwargs)

        def stream(self, **_kwargs: Any) -> Iterator[Any]:
            if False:
                yield None

    anth = _CountingAnth()
    events = list(
        run_ask_agent(
            question="count me",
            session=db_session,
            providers=[anth],  # type: ignore[list-item]
        )
    )
    finals = [e for e in events if e.type == "final"]
    assert finals
    # outer +1 then + (3-1) extras → provider_calls == 3
    assert finals[0].data.get("provider_calls") == 3
    assert anth.anthropic_attempts == 3


@pytest.mark.usefixtures("allow_llm")
def test_anthropic_exhaustion_mid_ask_falls_back_free(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from opspilot.agent.loop import run_ask_agent
    from opspilot.llm.types import AttemptStatus as AS

    class _ExhaustAnth:
        name = "anthropic"
        anthropic_attempts = 0

        def complete_json(self, **_kwargs: Any) -> ProviderResult:
            self.anthropic_attempts += 1
            return ProviderResult(status=AS.BUDGET_DENIED, model="claude", error_code="reservation_failed")

        def complete(self, **kwargs: Any) -> ProviderResult:
            return self.complete_json(**kwargs)

        def stream(self, **_kwargs: Any) -> Iterator[Any]:
            if False:
                yield None

    free = FakeProvider(
        name="gemini",
        json_results=[
            ProviderResult(
                status=AttemptStatus.SUCCESS,
                text=json.dumps({"kind": "final", "final": "from free"}),
                model="fake-v1",
            )
        ],
    )
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "100")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    events = list(
        run_ask_agent(
            question="fallback",
            session=db_session,
            providers=[_ExhaustAnth(), free],  # type: ignore[list-item]
        )
    )
    body = " ".join(str(e.data) for e in events)
    assert "from free" in body
