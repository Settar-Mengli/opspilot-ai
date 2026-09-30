"""CQ-05: shared HTTP error mapping preserves error codes."""

from __future__ import annotations

import httpx
import pytest

from opspilot.llm.providers.http import map_http_provider_result
from opspilot.llm.types import AttemptStatus


@pytest.mark.parametrize(
    ("status", "expected_code", "expected_status"),
    [
        (429, "429", AttemptStatus.RATE_LIMITED),
        (400, "http_400", AttemptStatus.ERROR),
        (500, "http_500", AttemptStatus.ERROR),
    ],
)
def test_map_http_provider_result_codes(status: int, expected_code: str, expected_status: AttemptStatus) -> None:
    request = httpx.Request("POST", "https://example.test/chat")
    response = httpx.Response(status, text='{"error":"x"}', request=request)
    if status == 429:
        response.headers["Retry-After"] = "1.5"
    result = map_http_provider_result(response=response, model="m", latency_ms=12)
    assert result is not None
    assert result.status is expected_status
    assert result.error_code == expected_code
    assert result.model == "m"
    assert result.latency_ms == 12
    if status == 429:
        assert result.retry_after_s == 1.5
    else:
        assert "provider_error" in result.meta


def test_map_http_success_returns_none() -> None:
    request = httpx.Request("POST", "https://example.test/chat")
    response = httpx.Response(200, text="{}", request=request)
    assert map_http_provider_result(response=response, model="m", latency_ms=1) is None
