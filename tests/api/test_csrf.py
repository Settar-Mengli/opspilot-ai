"""CSRF Origin checks + cookie SameSite/Secure flags."""

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


def test_disconnect_poller_stop_cancels_task() -> None:
    import asyncio

    from opspilot.api.v1.routes_ask import _disconnect_poller

    class _Req:
        async def is_disconnected(self) -> bool:
            await asyncio.sleep(0.01)
            return False

    async def _run() -> None:
        cancel_check, stop = _disconnect_poller(_Req())  # type: ignore[arg-type]
        assert cancel_check() is False
        task = getattr(stop, "task", None)
        assert task is not None
        stop()
        await asyncio.sleep(0.08)
        assert task.cancelled() or task.done()
        assert cancel_check() is False

    asyncio.run(_run())
