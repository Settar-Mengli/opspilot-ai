"""API soft-path proofs: FORCE_RULES / LLM_DISABLE never constructs Anthropic."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import app
from opspilot.api.deps import get_db_session, reset_db_engine


@pytest.fixture()
def soft_client(test_database_url: str, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")
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


def test_ask_under_force_rules_soft_and_no_anthropic(
    soft_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: list[bool] = []

    def _track(*_a, **_k):  # type: ignore[no-untyped-def]
        constructed.append(True)
        raise AssertionError("Anthropic must not be constructed")

    monkeypatch.setattr("anthropic.Anthropic", _track)
    resp = soft_client.post("/api/v1/ask", json={"question": "What needs attention?", "assistant_name": "OpsPilot"})
    assert resp.status_code == 200
    assert "answer" in resp.json()
    assert constructed == []


def test_evening_under_force_rules_soft_and_no_anthropic(
    soft_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: list[bool] = []

    def _track(*_a, **_k):  # type: ignore[no-untyped-def]
        constructed.append(True)
        raise AssertionError("Anthropic must not be constructed")

    monkeypatch.setattr("anthropic.Anthropic", _track)
    resp = soft_client.post("/api/v1/evening-summary", json={"assistant_name": "OpsPilot"})
    assert resp.status_code == 200
    assert "summary" in resp.json()
    assert constructed == []


def test_insights_under_force_rules_soft_and_no_anthropic(
    soft_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: list[bool] = []

    def _track(*_a, **_k):  # type: ignore[no-untyped-def]
        constructed.append(True)
        raise AssertionError("Anthropic must not be constructed")

    monkeypatch.setattr("anthropic.Anthropic", _track)
    resp = soft_client.post("/api/v1/insights", json={"assistant_name": "OpsPilot"})
    assert resp.status_code == 200
    body = resp.json()
    assert "intro" in body
    assert body["insights"] == []
    assert constructed == []


def test_llm_disable_blocks_ask_without_force_rules(
    test_database_url: str,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.setenv("OPSPILOT_LLM_DISABLE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")
    reset_db_engine()

    constructed: list[bool] = []

    def _track(*_a, **_k):  # type: ignore[no-untyped-def]
        constructed.append(True)
        raise AssertionError("Anthropic must not be constructed")

    monkeypatch.setattr("anthropic.Anthropic", _track)

    def _override() -> Iterator[Session]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db_session] = _override
    try:
        with TestClient(app) as test_client:
            resp = test_client.post(
                "/api/v1/ask",
                json={"question": "Hello?", "assistant_name": "OpsPilot"},
            )
            assert resp.status_code == 200
            assert constructed == []
    finally:
        app.dependency_overrides.clear()
        reset_db_engine()
