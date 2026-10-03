"""Error envelope tests (A6) — validation, HTTPException, unhandled 500."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from opspilot.api.app import app
from opspilot.api.deps import reset_db_engine


@pytest.fixture(autouse=True)
def _api_db(test_database_url: str, db_session):
    os.environ["DATABASE_URL"] = test_database_url
    reset_db_engine()
    yield
    reset_db_engine()


client = TestClient(app, raise_server_exceptions=False)


def test_envelope_validation_error_422():
    resp = client.post("/api/v1/runs", json={})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "validation_error"
    assert "message" in body["error"]
    assert "details" in body["error"]


def test_envelope_http_exception():
    resp = client.get("/api/v1/runs/run-does-not-exist-000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] in {"run_not_found", "http_error"}
    assert "message" in body["error"]
    assert "Traceback" not in resp.text


def test_envelope_unhandled_500_hides_internals(monkeypatch: pytest.MonkeyPatch):
    from sqlalchemy.orm import Session

    def _explode(self, *args, **kwargs):
        raise RuntimeError("secret stack detail should not leak")

    monkeypatch.setattr(Session, "execute", _explode)
    resp = client.get("/api/v1/runs")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert "secret stack" not in resp.text
    assert "Traceback" not in resp.text
    assert "RuntimeError" not in resp.text


def test_envelope_unhandled_500_logs_request_id_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy.orm import Session

    import opspilot.api.errors as errors_mod

    rid = "audit-500-rid-001"
    recorded: list[str] = []

    def _capture(msg: str, *args: object, **_kwargs: object) -> None:
        recorded.append(msg % args if args else msg)

    def _explode(self, *args, **kwargs):
        raise RuntimeError("password=hunter2 api_key=sk-ant-abcdefghijklmnop")

    monkeypatch.setattr(Session, "execute", _explode)
    monkeypatch.setattr(errors_mod.logger, "error", _capture)
    resp = client.get("/api/v1/runs", headers={"X-Request-ID": rid})
    assert resp.status_code == 500
    messages = [m for m in recorded if "unhandled_error" in m]
    assert messages, f"no unhandled_error log; recorded={recorded}"
    msg = messages[0]
    assert f"request_id={rid}" in msg
    assert "hunter2" not in msg
    assert "sk-ant-abcdefghijklmnop" not in msg


def test_settings_exact_key_set():
    resp = client.get("/api/v1/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "provider",
        "model",
        "api_key_set",
        "demo_mode",
        "google_connected",
        "last_morning",
        "last_sync",
    }
    assert "api_key_preview" not in body
    assert isinstance(body["api_key_set"], bool)
    assert isinstance(body["demo_mode"], bool)
    assert isinstance(body["google_connected"], bool)
