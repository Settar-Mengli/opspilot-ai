"""OBS-1: request_id propagation across pipeline worker threads + access log."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from opspilot.api.app import app
from opspilot.api.deps import get_db_session, reset_db_engine
from opspilot.llm.providers.fake import FakeProvider
from opspilot.persistence.models import LlmCallRow

_TRIAGE_JSON = json.dumps(
    {
        "urgency": "medium",
        "urgency_reason": "routine follow up",
        "category": "request",
        "category_reason": "user asked for help",
        "sentiment": "neutral",
        "sentiment_reason": "calm tone",
    }
)


@pytest.fixture()
def obs_client(test_database_url: str, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    reset_db_engine()

    fake = FakeProvider(
        name="gemini",
        json_responder=lambda *_a, **_k: _TRIAGE_JSON,
        text_responder=lambda task, _msgs: f"briefing:{task}",
    )

    def _providers() -> list[FakeProvider]:
        return [fake]

    monkeypatch.setattr("opspilot.llm.routing.build_providers", _providers)
    monkeypatch.setattr("opspilot.adapters.factory.build_providers", _providers)
    monkeypatch.setattr("opspilot.services._llm.build_providers", _providers)
    monkeypatch.setattr("opspilot.llm.policy.llm_allowed", lambda: True)
    monkeypatch.setattr("opspilot.llm.policy.force_rules_enabled", lambda: False)
    monkeypatch.setattr("opspilot.llm.routed.try_consume_request", lambda *a, **k: True)
    monkeypatch.setattr("opspilot.llm.routed.add_tokens", lambda *a, **k: None)

    from opspilot.adapters.gateway_triage import GatewayTriageAdapter

    monkeypatch.setattr(
        "opspilot.adapters.factory.get_adapter",
        lambda session=None: GatewayTriageAdapter(session=session),
    )

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


def test_post_runs_propagates_request_id_to_llm_calls(obs_client: TestClient, db_session: Session) -> None:
    rid = "e2e-req-id-obs1"
    resp = obs_client.post(
        "/api/v1/runs",
        json={"input_file": "sample_input.json", "date": "2026-05-29"},
        headers={"X-Request-ID": rid},
    )
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == rid

    rows = db_session.scalars(select(LlmCallRow)).all()
    assert rows, "expected LlmCall rows for triage/briefing gateway path"
    tasks = {r.task for r in rows}
    assert "triage" in tasks
    assert "briefing" in tasks
    for row in rows:
        if row.task in {"triage", "briefing"}:
            assert row.request_id == rid


def test_access_log_path_excludes_query_string(soft_access_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[str] = []

    def _capture(msg: str, *args: object, **_kwargs: object) -> None:
        recorded.append(msg % args if args else msg)

    monkeypatch.setattr("opspilot.api.app._access_logger.info", _capture)
    soft_access_client.get("/api/v1/health?secret=should-not-appear")
    joined = "\n".join(recorded)
    assert "path=/api/v1/health" in joined
    assert "secret=" not in joined
    assert "?" not in joined


@pytest.fixture()
def soft_access_client(
    test_database_url: str, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
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
