"""Hermetic tests for structured-output conversion, extract, empty reject, 400→json_object."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from opspilot.llm.budgets import utc_budget_day
from opspilot.llm.errors import LlmSchemaError
from opspilot.llm.json_extract import extract_json_object
from opspilot.llm.providers.fake import FakeProvider
from opspilot.llm.providers.gemini import GeminiProvider
from opspilot.llm.providers.openai_compatible import OpenAICompatibleProvider
from opspilot.llm.routed import BudgetAwareGateway, is_schema_format_http_error
from opspilot.llm.schema_convert import gemini_response_schema, groq_strict_schema
from opspilot.llm.schemas.insights import InsightsPayload
from opspilot.llm.types import AttemptStatus, Message, ProviderResult


@pytest.fixture()
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)


# --- Redacted real error bodies from S2 live diagnosis (keys scrubbed) ---
_GEMINI_S2_400 = (
    '{"error":{"code":400,"message":"Invalid JSON payload received. Unknown name \\"$defs\\" '
    'at \'generation_config.response_schema\': Cannot find field.","status":"INVALID_ARGUMENT"}}'
)
_GROQ_S2_400 = (
    '{"error":{"message":"\'messages\' : schema must have `additionalProperties` set to false '
    'in every object (missing on #/$defs/InsightItem)","type":"invalid_request_error"}}'
)


class _Item(BaseModel):
    title: str
    body: str = Field(min_length=1)


class _Payload(BaseModel):
    intro: str = Field(min_length=1)
    insights: list[_Item] = Field(min_length=1)


def test_gemini_schema_inlines_refs_no_defs() -> None:
    schema = gemini_response_schema(InsightsPayload)
    dumped = json.dumps(schema)
    assert "$ref" not in dumped
    assert "$defs" not in dumped
    assert "definitions" not in dumped
    assert schema.get("type") == "object"
    assert "insights" in (schema.get("properties") or {})


def test_groq_strict_additional_properties_on_defs() -> None:
    schema = groq_strict_schema(InsightsPayload)
    assert schema.get("additionalProperties") is False
    defs = schema.get("$defs") or {}
    if "InsightItem" in defs:
        assert defs["InsightItem"].get("additionalProperties") is False
        props = defs["InsightItem"].get("properties") or {}
        required = set(defs["InsightItem"].get("required") or [])
        assert required == set(props.keys())


def test_extract_json_from_fence_and_prose() -> None:
    fenced = 'Here you go:\n```json\n{"intro":"a","insights":[{"title":"t","body":"b"}]}\n```\n'
    out = extract_json_object(fenced)
    assert json.loads(out)["intro"] == "a"
    wrapped = 'Sure. {"intro":"x","insights":[{"title":"t","body":"b","category":"general"}]} Thanks.'
    assert json.loads(extract_json_object(wrapped))["intro"] == "x"


def test_empty_insights_list_rejected() -> None:
    with pytest.raises(ValidationError):
        InsightsPayload.model_validate({"intro": "hi", "insights": []})


def test_is_schema_format_http_error_from_s2_bodies() -> None:
    gem = ProviderResult(
        status=AttemptStatus.ERROR,
        error_code="http_400",
        model="gemini-3.5-flash-lite",
        meta={"status_code": 400, "provider_error": _GEMINI_S2_400},
    )
    groq = ProviderResult(
        status=AttemptStatus.ERROR,
        error_code="http_400",
        model="openai/gpt-oss-20b",
        meta={"status_code": 400, "provider_error": _GROQ_S2_400},
    )
    other = ProviderResult(
        status=AttemptStatus.ERROR,
        error_code="http_400",
        model="x",
        meta={"status_code": 400, "provider_error": "quota exceeded"},
    )
    assert is_schema_format_http_error(gem) is True
    assert is_schema_format_http_error(groq) is True
    assert is_schema_format_http_error(other) is False


@pytest.mark.usefixtures("allow_llm")
def test_gemini_sends_inlined_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        seen["schema"] = (body.get("generationConfig") or {}).get("responseSchema")
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "intro": "ok",
                                            "insights": [{"title": "t", "body": "b", "category": "general"}],
                                        }
                                    )
                                }
                            ]
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 10},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GeminiProvider(client=client)
    result = provider.complete_json(
        task="insights",
        messages=[Message(role="user", content="queue: 1 items")],
        schema=InsightsPayload,
        max_tokens=512,
    )
    assert result.status is AttemptStatus.SUCCESS
    dumped = json.dumps(seen["schema"])
    assert "$defs" not in dumped
    assert "$ref" not in dumped
    client.close()


@pytest.mark.usefixtures("allow_llm")
def test_groq_strict_schema_on_wire(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        seen["rf"] = body.get("response_format")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "intro": "ok",
                                    "insights": [{"title": "t", "body": "b", "category": "g"}],
                                }
                            )
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 8},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = OpenAICompatibleProvider("groq", client=client).complete_json(
        task="insights",
        messages=[Message(role="user", content="x")],
        schema=InsightsPayload,
        max_tokens=512,
    )
    assert result.status is AttemptStatus.SUCCESS
    js = seen["rf"]["json_schema"]["schema"]
    assert js.get("additionalProperties") is False
    defs = js.get("$defs") or {}
    if "InsightItem" in defs:
        assert defs["InsightItem"].get("additionalProperties") is False
    client.close()


@pytest.mark.usefixtures("allow_llm")
def test_400_schema_retry_json_object_then_ok(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "20")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    day = utc_budget_day()
    db_session.execute(text("DELETE FROM llm_budget_counters WHERE day_utc = :d"), {"d": day})
    db_session.commit()

    calls: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        gc = body.get("generationConfig") or {}
        calls.append({"has_schema": "responseSchema" in gc, "mime": gc.get("responseMimeType")})
        if "responseSchema" in gc:
            return httpx.Response(400, text=_GEMINI_S2_400)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "intro": "recovered",
                                            "insights": [{"title": "t", "body": "b", "category": "general"}],
                                        }
                                    )
                                }
                            ]
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 2, "candidatesTokenCount": 12},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    recorded: list[ProviderResult] = []

    def recorder(**kwargs: Any) -> None:
        recorded.append(kwargs["result"])

    gw = BudgetAwareGateway(
        [GeminiProvider(client=client)],
        session=db_session,
        recorder=recorder,
        observe=False,
    )
    out = gw.complete_json(
        task="insights",
        messages=[Message(role="user", content="queue: 1")],
        schema=_Payload,
        max_tokens=512,
    )
    assert out.intro == "recovered"
    assert len(calls) == 2
    assert calls[0]["has_schema"] is True
    assert calls[1]["has_schema"] is False
    # One LlmCall-equivalent row per attempt: schema 400 + success
    assert len(recorded) == 2
    assert recorded[0].status is AttemptStatus.ERROR
    assert recorded[0].error_code == "http_400"
    assert recorded[1].status is AttemptStatus.SUCCESS
    client.close()


@pytest.mark.usefixtures("allow_llm")
def test_fenced_output_extract_and_empty_failover(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "20")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_REQ_DAY", "20")
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_TOK_DAY", "100000")
    day = utc_budget_day()
    db_session.execute(text("DELETE FROM llm_budget_counters WHERE day_utc = :d"), {"d": day})
    db_session.commit()

    degenerate = FakeProvider(
        name="gemini",
        json_results=[
            ProviderResult(
                status=AttemptStatus.SUCCESS,
                text='{"intro":"x","insights":[]}',
                model="fake-v1",
                input_tokens=1,
                output_tokens=7,
            ),
            ProviderResult(
                status=AttemptStatus.SUCCESS,
                text='{"intro":"x","insights":[]}',
                model="fake-v1",
                input_tokens=1,
                output_tokens=7,
            ),
        ],
    )
    fenced_ok = FakeProvider(
        name="groq",
        json_responder=lambda *_a: '```json\n{"intro":"ok","insights":[{"title":"T","body":"B"}]}\n```',
    )
    recorded: list[tuple[str, AttemptStatus, dict[str, Any]]] = []

    def recorder(**kwargs: Any) -> None:
        result: ProviderResult = kwargs["result"]
        recorded.append((kwargs["provider"], result.status, dict(result.meta or {})))

    gw = BudgetAwareGateway(
        [degenerate, fenced_ok],
        session=db_session,
        recorder=recorder,
        observe=False,
    )
    out = gw.complete_json(
        task="insights",
        messages=[Message(role="user", content="queue: 2")],
        schema=_Payload,
        max_tokens=512,
    )
    assert out.intro == "ok"
    assert out.insights[0].title == "T"
    assert any(m.get("error_class") == "schema_validation" for _, _, m in recorded)
    assert any(p == "groq" and s is AttemptStatus.SUCCESS for p, s, _ in recorded)


@pytest.mark.usefixtures("allow_llm")
def test_all_empty_insights_raise_schema_error(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "20")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    day = utc_budget_day()
    db_session.execute(text("DELETE FROM llm_budget_counters WHERE day_utc = :d"), {"d": day})
    db_session.commit()

    bad = FakeProvider(
        name="gemini",
        json_responder=lambda *_a: '{"intro":"hi","insights":[]}',
    )
    gw = BudgetAwareGateway([bad], session=db_session, observe=False)
    with pytest.raises(LlmSchemaError):
        gw.complete_json(
            task="insights",
            messages=[Message(role="user", content="queue: 1")],
            schema=_Payload,
            max_tokens=256,
        )
