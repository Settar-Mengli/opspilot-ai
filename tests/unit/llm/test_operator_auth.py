"""OperatorAnthropicAuth minting guards (A6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from itsdangerous import URLSafeTimedSerializer

from opspilot.llm.operator_auth import OperatorAnthropicAuth
from opspilot.services.operator_session import OperatorSession, issue_session, verify_session


def test_operator_auth_from_session_ok() -> None:
    session = OperatorSession(
        role="demo_operator",
        email="op@example.test",
        exp=datetime.now(UTC) + timedelta(hours=1),
    )
    auth = OperatorAnthropicAuth.from_session(session)
    assert auth is not None
    assert auth.role == "demo_operator"


def test_operator_auth_from_session_none() -> None:
    assert OperatorAnthropicAuth.from_session(None) is None


def test_operator_auth_from_session_wrong_role() -> None:
    session = OperatorSession(
        role="visitor",
        email="v@example.test",
        exp=datetime.now(UTC) + timedelta(hours=1),
    )
    assert OperatorAnthropicAuth.from_session(session) is None


def test_operator_auth_from_session_forged_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-secret-for-auth-a6")
    good = issue_session(email="op@example.test")
    assert verify_session(good) is not None
    forged = good[:-4] + ("AAAA" if not good.endswith("AAAA") else "BBBB")
    assert verify_session(forged) is None
    assert OperatorAnthropicAuth.from_session(verify_session(forged)) is None


def test_operator_auth_from_session_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-secret-for-auth-a6")
    ser = URLSafeTimedSerializer("test-secret-for-auth-a6", salt="opspilot-operator-session")
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    token = ser.dumps({"role": "demo_operator", "email": "op@example.test", "exp": past})
    assert verify_session(token) is None
    assert OperatorAnthropicAuth.from_session(verify_session(token)) is None
