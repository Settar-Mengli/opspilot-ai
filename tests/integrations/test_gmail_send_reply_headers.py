"""send_reply In-Reply-To / References from RFC Message-ID only (never synthesize)."""

from __future__ import annotations

import base64
from email import message_from_bytes

import httpx
import pytest

from opspilot.integrations.gmail_client import GmailClient
from opspilot.integrations.google_http import GoogleHttpError


class _MetaCaptureTransport:
    def __init__(self, *, rfc_message_id: str | None) -> None:
        self.rfc_message_id = rfc_message_id
        self.last_json: dict | None = None
        self.gets: list[dict] = []

    def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
        if method.upper() == "GET":
            self.gets.append({"url": url, "params": kwargs.get("params")})
            headers = []
            if self.rfc_message_id:
                headers.append({"name": "Message-ID", "value": self.rfc_message_id})
            return httpx.Response(200, json={"id": "msg1", "payload": {"headers": headers}})
        self.last_json = kwargs.get("json")
        return httpx.Response(200, json={"id": "sent_1"})


def test_send_reply_sets_headers_from_rfc_message_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.test")
    tx = _MetaCaptureTransport(rfc_message_id="<orig@example.test>")
    client = GmailClient(access_token="tok", transport=tx)
    mid = client.send_reply(
        thread_id="thr1",
        in_reply_to_provider_id="gmail_opaque_1",
        to_addrs="demo@example.test",
        subject="Re: FIXTURE_SUBJECT",
        body="FIXTURE_BODY",
    )
    assert mid == "sent_1"
    assert tx.gets and tx.gets[0]["params"]["format"] == "metadata"
    assert tx.last_json is not None
    assert tx.last_json["threadId"] == "thr1"
    raw_b64 = str(tx.last_json["raw"])
    pad = "=" * (-len(raw_b64) % 4)
    msg = message_from_bytes(base64.urlsafe_b64decode(raw_b64 + pad))
    assert msg["In-Reply-To"] == "<orig@example.test>"
    assert msg["References"] == "<orig@example.test>"
    assert msg["To"] == "demo@example.test"


def test_send_reply_omits_headers_when_rfc_message_id_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.test")
    tx = _MetaCaptureTransport(rfc_message_id=None)
    client = GmailClient(access_token="tok", transport=tx)
    mid = client.send_reply(
        thread_id="thr2",
        in_reply_to_provider_id="gmail_opaque_2",
        to_addrs="demo@example.test",
        subject="Re: FIXTURE_SUBJECT",
        body="FIXTURE_BODY",
    )
    assert mid == "sent_1"
    assert tx.last_json is not None
    assert tx.last_json["threadId"] == "thr2"
    raw_b64 = str(tx.last_json["raw"])
    pad = "=" * (-len(raw_b64) % 4)
    msg = message_from_bytes(base64.urlsafe_b64decode(raw_b64 + pad))
    assert msg["In-Reply-To"] is None
    assert msg["References"] is None
    # Never synthesize provider id into threading headers.
    assert "gmail_opaque_2" not in (msg.as_string())


def test_get_message_rfc_message_id_raises_on_http_error() -> None:
    class Boom:
        def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
            return httpx.Response(404, json={"error": "not found"})

    client = GmailClient(access_token="tok", transport=Boom())  # type: ignore[arg-type]
    with pytest.raises(GoogleHttpError):
        client.get_message_rfc_message_id("missing")
