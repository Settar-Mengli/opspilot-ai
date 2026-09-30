"""API soft-200 shape tests for ask / evening / insights (D-01)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import app
from opspilot.api.deps import get_db_session, reset_db_engine


@pytest.fixture()
def api_client(test_database_url: str, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
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


def test_ask_soft_shape(api_client: TestClient) -> None:
    resp = api_client.post("/api/v1/ask", json={"question": "What needs attention?", "assistant_name": "OpsPilot"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"answer"}
    assert isinstance(body["answer"], str)
    assert body["answer"]


def test_evening_soft_shape(api_client: TestClient) -> None:
    resp = api_client.post("/api/v1/evening-summary", json={"assistant_name": "OpsPilot"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"summary"}
    assert isinstance(body["summary"], str)


def test_insights_soft_shape(api_client: TestClient) -> None:
    resp = api_client.post("/api/v1/insights", json={"assistant_name": "OpsPilot"})
    assert resp.status_code == 200
    body = resp.json()
    assert "intro" in body
    assert "insights" in body
    assert isinstance(body["insights"], list)
