"""SSE Ask stream API tests."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import app
from opspilot.api.deps import get_db_session, reset_db_engine
from opspilot.llm.providers.fake import FakeProvider
from opspilot.llm.types import AttemptStatus, ProviderResult


@pytest.fixture()
def api_client(test_database_url: str, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "100")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
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


def test_ask_stream_sse_final(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeProvider(
        name="gemini",
        json_results=[
            ProviderResult(
                status=AttemptStatus.SUCCESS,
                text=json.dumps({"kind": "final", "final": "Hello from stream"}),
                model="fake-v1",
                input_tokens=5,
                output_tokens=5,
                latency_ms=1,
            )
        ],
    )
    monkeypatch.setattr("opspilot.agent.loop.build_providers", lambda: [fake])
    resp = api_client.post("/api/v1/ask/stream", json={"question": "Hi", "assistant_name": "OpsPilot"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    body = resp.text
    assert "data: " in body
    assert "Hello from stream" in body
    assert '"type": "final"' in body or '"type":"final"' in body
