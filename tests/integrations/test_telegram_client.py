"""Telegram morning outcome client (counts-only)."""

from __future__ import annotations

from datetime import date

import httpx

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


def test_send_outcome_success() -> None:
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


def test_send_outcome_http_fail_returns_code() -> None:
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


def test_httpx_transport_uses_injected_client() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"ok": True})))
    tx = HttpxTelegramTransport(client=client)
    resp = tx.request("GET", "https://example.test/")
    assert resp.status_code == 200
    client.close()
