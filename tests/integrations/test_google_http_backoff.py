"""Google HTTP refresh + bounded backoff helpers."""

from __future__ import annotations

import httpx
import pytest

from opspilot.integrations.google_http import GoogleHttpError, refresh_access_token, request_with_backoff


class _SeqTransport:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
        self.calls += 1
        if not self._responses:
            raise AssertionError("no responses left")
        return self._responses.pop(0)


def test_refresh_invalid_grant_raises() -> None:
    tx = _SeqTransport([httpx.Response(400, json={"error": "invalid_grant"})])
    with pytest.raises(GoogleHttpError) as exc:
        refresh_access_token(
            client_id="cid",
            client_secret="sec",
            refresh_token="rt",
            transport=tx,
        )
    assert str(exc.value.args[0]) == "invalid_grant"
    assert exc.value.status_code == 400


def test_request_with_backoff_retries_429_then_ok() -> None:
    sleeps: list[float] = []
    tx = _SeqTransport(
        [
            httpx.Response(429, headers={"Retry-After": "0.1"}, json={"error": "rate"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    resp = request_with_backoff(
        tx,
        "GET",
        "https://example.test/x",
        sleep=sleeps.append,
    )
    assert resp.status_code == 200
    assert tx.calls == 2
    assert sleeps == [0.1]


def test_request_with_backoff_wall_cap_stops_retries() -> None:
    sleeps: list[float] = []
    # First 8s sleep OK; second 8s would make cumulative 16 > 15 → stop without sleeping again.
    tx = _SeqTransport(
        [
            httpx.Response(503, headers={"Retry-After": "8"}, json={"error": "a"}),
            httpx.Response(503, headers={"Retry-After": "8"}, json={"error": "b"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    resp = request_with_backoff(
        tx,
        "GET",
        "https://example.test/x",
        sleep=sleeps.append,
    )
    assert sleeps == [8.0]
    assert sum(sleeps) <= 15.0
    assert resp.status_code == 503
    assert tx.calls == 2


def test_request_with_backoff_cumulative_sleep_at_most_15s() -> None:
    sleeps: list[float] = []
    # Force several retries with 8s capped sleeps; wall cap must stop before sum > 15.
    tx = _SeqTransport(
        [
            httpx.Response(503, json={"error": "a"}),
            httpx.Response(503, json={"error": "b"}),
            httpx.Response(503, json={"error": "c"}),
            httpx.Response(503, json={"error": "d"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    resp = request_with_backoff(
        tx,
        "GET",
        "https://example.test/x",
        sleep=sleeps.append,
    )
    assert sum(sleeps) <= 15.0
    assert resp.status_code in {503, 200}


def test_request_with_backoff_rejects_post_retry_without_opt_in() -> None:
    sleeps: list[float] = []
    tx = _SeqTransport(
        [
            httpx.Response(503, json={"error": "a"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    resp = request_with_backoff(
        tx,
        "POST",
        "https://example.test/x",
        sleep=sleeps.append,
    )
    assert resp.status_code == 503
    assert tx.calls == 1
    assert sleeps == []


def test_request_with_backoff_post_retries_when_opted_in() -> None:
    sleeps: list[float] = []
    tx = _SeqTransport(
        [
            httpx.Response(503, headers={"Retry-After": "0.1"}, json={"error": "a"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    resp = request_with_backoff(
        tx,
        "POST",
        "https://example.test/x",
        sleep=sleeps.append,
        allow_retry_non_idempotent=True,
    )
    assert resp.status_code == 200
    assert tx.calls == 2
    assert sleeps == [0.1]
