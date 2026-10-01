"""CSRF Origin checks + cookie SameSite/Secure flags."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.responses import Response

from opspilot.api.app import app
from opspilot.api.deps import get_db_session, reset_db_engine
from opspilot.services.operator_session import COOKIE_NAME, set_operator_cookie


@pytest.fixture()
def api_client(test_database_url: str, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-for-csrf-32b!!")
    monkeypatch.setenv("OPSPILOT_CORS_ORIGINS", "http://127.0.0.1:5173")
    monkeypatch.delenv("OPSPILOT_CSRF_RELAX_DEV", raising=False)
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


def test_csrf_missing_origin_rejected(api_client: TestClient) -> None:
    resp = api_client.post("/api/v1/ask/stream", json={"question": "Hi", "assistant_name": "OpsPilot"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "csrf_origin_rejected"


def test_csrf_bad_origin_rejected(api_client: TestClient) -> None:
    resp = api_client.post(
        "/api/v1/ask/stream",
        json={"question": "Hi", "assistant_name": "OpsPilot"},
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "csrf_origin_rejected"


def test_csrf_allowed_origin_passes_gate(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "opspilot.api.v1.routes_ask.run_ask_agent",
        lambda **_kwargs: iter([]),
    )
    resp = api_client.post(
        "/api/v1/ask/stream",
        json={"question": "Hi", "assistant_name": "OpsPilot"},
        headers={"Origin": "http://127.0.0.1:5173"},
    )
    assert resp.status_code == 200


def test_cookie_samesite_lax_and_secure_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-for-cookie-32b!")
    monkeypatch.setenv("OPSPILOT_COOKIE_SECURE", "1")
    response = Response()
    set_operator_cookie(response, email="ops@example.com")
    raw = response.headers.get("set-cookie") or ""
    assert COOKIE_NAME in raw
    assert "samesite=lax" in raw.lower()
    assert "secure" in raw.lower()
