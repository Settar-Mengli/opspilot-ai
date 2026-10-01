"""Operator session cookie (L8 + A1)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.responses import Response

COOKIE_NAME = "opspilot_operator"
_MAX_AGE_SECONDS = 7 * 24 * 3600


class SessionUnavailableError(RuntimeError):
    """OPSPILOT_SESSION_SECRET missing or invalid session."""


@dataclass(frozen=True)
class OperatorSession:
    role: str
    email: str
    exp: datetime


def _serializer() -> URLSafeTimedSerializer:
    secret = os.environ.get("OPSPILOT_SESSION_SECRET", "").strip()
    if not secret:
        raise SessionUnavailableError("OPSPILOT_SESSION_SECRET is not set")
    return URLSafeTimedSerializer(secret, salt="opspilot-operator-session")


def issue_session(*, email: str, role: str = "demo_operator") -> str:
    exp = datetime.now(UTC) + timedelta(seconds=_MAX_AGE_SECONDS)
    payload: dict[str, Any] = {"role": role, "email": email, "exp": exp.isoformat()}
    return _serializer().dumps(payload)


def verify_session(token: str | None) -> OperatorSession | None:
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired, SessionUnavailableError):
        return None
    if not isinstance(data, dict):
        return None
    role = str(data.get("role") or "")
    email = str(data.get("email") or "")
    exp_raw = data.get("exp")
    if role != "demo_operator" or not email or not exp_raw:
        return None
    try:
        exp = datetime.fromisoformat(str(exp_raw))
    except ValueError:
        return None
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    if exp < datetime.now(UTC):
        return None
    return OperatorSession(role=role, email=email, exp=exp)


def set_operator_cookie(response: Response, *, email: str) -> None:
    token = issue_session(email=email)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=_MAX_AGE_SECONDS,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


def clear_operator_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def demo_mode_enabled() -> bool:
    return os.environ.get("OPSPILOT_DEMO_MODE", "0").strip().lower() in {"1", "true", "yes"}
