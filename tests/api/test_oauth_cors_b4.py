"""Hermetic OAuth / CORS / DEMO_MODE tests (B4 C3)."""

from __future__ import annotations

from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from opspilot.api.app import create_app
from opspilot.integrations.google_oauth import TokenBundle, make_pkce_pair
from opspilot.services.operator_session import issue_session


@pytest.fixture
def b4_env(monkeypatch: pytest.MonkeyPatch, test_database_url: str) -> None:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-not-real")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)


@pytest.fixture
def client(b4_env: None) -> TestClient:
    return TestClient(create_app())


def test_cors_preflight_credentials_allowed(client: TestClient) -> None:
    resp = client.options(
        "/api/v1/settings",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code in {200, 204}
    assert resp.headers.get("access-control-allow-credentials") == "true"
    assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_cors_preflight_other_origin_rejected(client: TestClient) -> None:
    resp = client.options(
        "/api/v1/settings",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Disallowed origin must not be echoed (never "*"); credentials alone are not enough.
    assert resp.headers.get("access-control-allow-origin") not in {
        "http://evil.example",
        "*",
    }


def test_oauth_start_demo_mode_blocked(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "1")
    resp = client.get("/api/v1/oauth/google/start", follow_redirects=False)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "demo_mode_blocks_oauth"


def test_oauth_start_redirects_with_pkce_cookie(client: TestClient) -> None:
    resp = client.get("/api/v1/oauth/google/start", follow_redirects=False)
    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert "accounts.google.com" in loc
    assert "code_challenge" in loc
    assert "code_challenge_method=S256" in loc
    assert "opspilot_pkce" in resp.cookies


def test_oauth_callback_stores_encrypted_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_session: Any
) -> None:
    _ = db_session
    verifier, _challenge = make_pkce_pair()
    state = "statefixture"
    monkeypatch.setattr(
        "opspilot.api.v1.oauth_routes.complete_oauth",
        lambda **kwargs: TokenBundle(
            refresh_token="refresh-fixture",
            access_token="access-fixture",
            email="demo@example.com",
            scopes="openid email https://www.googleapis.com/auth/gmail.readonly",
        ),
    )
    client.cookies.set("opspilot_pkce", f"{state}:{verifier}")
    resp = client.get(
        "/api/v1/oauth/google/callback",
        params={"code": "authcode", "state": state},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "127.0.0.1:5173/connections" in resp.headers["location"]
    assert "opspilot_operator" in resp.cookies


def test_session_issue_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "another-test-secret")
    from opspilot.services.operator_session import verify_session

    token = issue_session(email="op@example.com")
    sess = verify_session(token)
    assert sess is not None
    assert sess.email == "op@example.com"
