"""Startup config + access logger visibility."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from opspilot.api import app as app_mod
from opspilot.api.app import app
from opspilot.api.startup_config import ensure_api_logging, log_startup_config


def test_log_startup_config_non_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "a@example.com,b@example.com")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "false")
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    sink = MagicMock()
    line = log_startup_config(logger=sink)
    sink.info.assert_called()
    assert "FORCE_RULES=0" in line
    assert "DEMO_MODE=0" in line
    assert "allowlist_count=2" in line
    assert "ANTHROPIC_ENABLED=0" in line
    assert "sk-" not in line
    assert "@example.com" not in line


def test_access_logger_emits_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_CSRF_RELAX_DEV", "1")
    ensure_api_logging()
    lines: list[str] = []

    def _capture(msg: str, *args: object, **_kwargs: object) -> None:
        lines.append(msg % args if args else str(msg))

    monkeypatch.setattr(app_mod._access_logger, "info", _capture)
    client = TestClient(app)
    resp = client.get("/api/v1/health", headers={"X-Request-ID": "access-log-rid-1"})
    assert resp.status_code == 200
    joined = "\n".join(lines)
    assert "path=/api/v1/health" in joined
    assert "request_id=access-log-rid-1" in joined


def test_ensure_api_logging_sets_info_levels() -> None:
    ensure_api_logging()
    assert logging.getLogger("opspilot.api.access").level == logging.INFO
    assert logging.getLogger("opspilot.api.ask").level == logging.INFO
