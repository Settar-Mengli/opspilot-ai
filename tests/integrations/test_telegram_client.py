"""Telegram morning outcome client (counts-only)."""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from opspilot.integrations import telegram_client as tg
from opspilot.integrations.telegram_client import (
    HttpxTelegramTransport,
    MorningOutcomeFields,
    format_outcome_message,
    send_outcome_message,
)


class _SeqTransport:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self.last_json: dict[str, object] | None = None

    def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        self.last_json = kwargs.get("json")  # type: ignore[assignment]
        if not self._responses:
            raise AssertionError("no responses left")
        return self._responses.pop(0)


class _BoomTransport:
    def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("connection refused")


def test_send_outcome_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    tx = _SeqTransport([httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})])
    fields = MorningOutcomeFields(status="succeeded", day_utc=date(2026, 10, 3), triaged=2)
    err = send_outcome_message(
        fields,
        transport=tx,
        bot_token="tok",
        chat_id="99",
    )
    assert err is None
    assert tx.last_json is not None
    assert tx.last_json["chat_id"] == "99"
    text = str(tx.last_json["text"])
    assert "status=succeeded" in text
    assert "triaged=2" in text


def test_send_outcome_http_fail_returns_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    tx = _SeqTransport([httpx.Response(502, text="bad gateway")])
    fields = MorningOutcomeFields(status="succeeded", day_utc=date(2026, 10, 3))
    err = send_outcome_message(fields, transport=tx, bot_token="tok", chat_id="1")
    assert err == "http_502"


def test_format_outcome_message_includes_error_code() -> None:
    fields = MorningOutcomeFields(
        status="failed",
        day_utc=date(2026, 10, 3),
        error_code="drain_busy",
    )
    msg = format_outcome_message(fields)
    assert "error_code=drain_busy" in msg
    assert "urgency_C/H/M/L=0/0/0/0" in msg


def test_httpx_transport_uses_injected_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"ok": True})))
    tx = HttpxTelegramTransport(client=client)
    resp = tx.request("GET", "https://example.test/")
    assert resp.status_code == 200
    client.close()


def test_network_error_local_uses_exc_info(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    seen: list[dict[str, object]] = []

    def _capture(msg: str, *args: object, **kwargs: object) -> None:
        seen.append({"msg": msg % args if args else msg, "exc_info": kwargs.get("exc_info")})

    monkeypatch.setattr(tg.logger, "warning", _capture)
    err = send_outcome_message(
        MorningOutcomeFields(status="succeeded", day_utc=date(2026, 10, 3)),
        transport=_BoomTransport(),
        bot_token="tok",
        chat_id="1",
    )
    assert err == "telegram_network_error"
    assert seen
    assert seen[0]["exc_info"] is True


def test_network_error_gha_codes_only_no_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("CI", "true")
    seen: list[dict[str, object]] = []

    def _capture(msg: str, *args: object, **kwargs: object) -> None:
        seen.append({"msg": msg % args if args else msg, "exc_info": kwargs.get("exc_info")})

    monkeypatch.setattr(tg.logger, "warning", _capture)
    err = send_outcome_message(
        MorningOutcomeFields(status="succeeded", day_utc=date(2026, 10, 3)),
        transport=_BoomTransport(),
        bot_token="tok",
        chat_id="1",
    )
    assert err == "telegram_network_error"
    assert seen
    joined = seen[0]["msg"]
    assert isinstance(joined, str)
    assert "error_code=telegram_network_error" in joined
    assert "exc_type=ConnectError" in joined
    assert seen[0].get("exc_info") in (None, False)
    assert "connection refused" not in joined
