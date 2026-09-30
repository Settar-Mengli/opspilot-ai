"""P13: structured complete_json sends temperature=0."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from opspilot.llm.providers.openai_compatible import OpenAICompatibleProvider
from opspilot.llm.schemas.insights import InsightsPayload
from opspilot.llm.types import Message


def test_openai_compatible_structured_includes_temperature_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read()
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"intro":"x","insights":[{"title":"t","body":"b","category":"general"}]}'}}
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = OpenAICompatibleProvider("groq", client=client)
    provider.complete_json(
        task="insights",
        messages=[Message(role="user", content="hi")],
        schema=InsightsPayload,
        max_tokens=100,
        temperature=0.0,
    )
    body = json.loads(captured["body"].decode())
    assert body.get("temperature") == 0.0
