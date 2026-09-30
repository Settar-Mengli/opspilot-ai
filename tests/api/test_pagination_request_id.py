"""API tests for pagination, request_id, and F-03 sanitization."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import app
from opspilot.api.deps import get_db_session, reset_db_engine
from opspilot.persistence.models import RunRow
from opspilot.utils.logging_utils import redact_fields


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


def test_list_runs_default_limit(api_client: TestClient, db_session: Session) -> None:
    for i in range(3):
        db_session.add(
            RunRow(
                run_id=f"run-{i}",
                finished_at=datetime(2026, 9, 20 + i, 12, 0, tzinfo=UTC),
                status="success",
                metadata_json={"run_id": f"run-{i}"},
            )
        )
    db_session.commit()
    resp = api_client.get("/api/v1/runs")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 3


def test_list_runs_limit_and_cursor(api_client: TestClient, db_session: Session) -> None:
    for i in range(5):
        db_session.add(
            RunRow(
                run_id=f"c-run-{i}",
                finished_at=datetime(2026, 9, 10 + i, 12, 0, tzinfo=UTC),
                status="success",
                metadata_json={"run_id": f"c-run-{i}"},
            )
        )
    db_session.commit()
    first = api_client.get("/api/v1/runs", params={"limit": 2})
    assert first.status_code == 200
    page1 = first.json()
    assert len(page1) == 2
    cursor = page1[-1]["run_id"]
    second = api_client.get("/api/v1/runs", params={"limit": 2, "cursor": cursor})
    assert second.status_code == 200
    page2 = second.json()
    assert len(page2) == 2
    assert {r["run_id"] for r in page1}.isdisjoint({r["run_id"] for r in page2})


def test_request_id_echo(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/health", headers={"X-Request-ID": "client-req-1"})
    assert resp.headers.get("X-Request-ID") == "client-req-1"


def test_request_id_rejects_illegal_and_oversized(api_client: TestClient) -> None:
    bad = api_client.get("/api/v1/health", headers={"X-Request-ID": "bad id with spaces!"})
    assert bad.headers.get("X-Request-ID") != "bad id with spaces!"
    assert bad.headers.get("X-Request-ID")
    oversized = "a" * 65
    big = api_client.get("/api/v1/health", headers={"X-Request-ID": oversized})
    assert big.headers.get("X-Request-ID") != oversized
    assert len(big.headers.get("X-Request-ID", "")) <= 64


def test_validation_details_sanitized(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_DEBUG_ERRORS", raising=False)
    resp = api_client.post("/api/v1/ask", json={})
    assert resp.status_code == 422
    details = resp.json()["error"]["details"]
    assert isinstance(details, list)
    for item in details:
        assert "msg" not in item
        assert "input" not in item
        assert "type" in item


def test_redact_fields() -> None:
    out = redact_fields({"api_key": "sk-secret", "task": "ask", "token": "abc"})
    assert out["api_key"] == "***"
    assert out["token"] == "***"
    assert out["task"] == "ask"
