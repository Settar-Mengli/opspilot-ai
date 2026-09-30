"""Groq strict schema + triage token headroom hermetic checks."""

from __future__ import annotations

from opspilot.adapters.gateway_triage import _STRUCTURED_MAX_TOKENS
from opspilot.evals.live import TRIAGE_STRUCTURED_MAX_TOKENS
from opspilot.llm.routed import is_schema_format_http_error
from opspilot.llm.schema_convert import groq_strict_schema
from opspilot.llm.schemas.triage import TriagePayload
from opspilot.llm.types import AttemptStatus, ProviderResult


def test_triage_structured_max_tokens_headroom() -> None:
    """Groq constrained decode needs >300 tokens for P12 TriagePayload."""
    assert TRIAGE_STRUCTURED_MAX_TOKENS >= 1024
    assert _STRUCTURED_MAX_TOKENS == TRIAGE_STRUCTURED_MAX_TOKENS


def test_groq_strict_schema_meets_documented_rules() -> None:
    """additionalProperties:false + all properties required (Groq strict docs)."""
    schema = groq_strict_schema(TriagePayload)
    assert schema.get("type") == "object"
    assert schema.get("additionalProperties") is False
    props = schema["properties"]
    required = set(schema["required"])
    assert required == set(props.keys())
    # P12 fields present; length/bounds retained (not rejected by Groq docs subset).
    assert "confidence" in props
    assert props["confidence"].get("minimum") == 0.0
    assert props["confidence"].get("maximum") == 1.0
    assert "evidence_refs" in props
    assert props["evidence_refs"].get("maxItems") == 16
    assert props["urgency_reason"].get("minLength") == 1


def test_groq_max_completion_tokens_triggers_json_object_retry_hint() -> None:
    result = ProviderResult(
        status=AttemptStatus.ERROR,
        error_code="http_400",
        model="openai/gpt-oss-20b",
        meta={
            "status_code": 400,
            "provider_error": (
                '{"error":{"message":"Failed to generate JSON...",'
                '"code":"json_validate_failed",'
                '"failed_generation":"max completion tokens reached before generating a valid document"}}'
            ),
        },
    )
    assert is_schema_format_http_error(result) is True
