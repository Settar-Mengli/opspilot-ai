"""Hermetic tests for instance-contract prompts + schema-echo unwrap (D-LIVE-1)."""

from __future__ import annotations

import json

from opspilot.llm.routed import BudgetAwareGateway
from opspilot.llm.schema_convert import (
    instance_schema_prompt,
    schema_prompt_fragment,
    unwrap_schema_echo,
)
from opspilot.llm.schemas.triage import TriagePayload

# Redacted Mistral live failure head (schema-echo under properties).
_MISTRAL_SCHEMA_ECHO = {
    "description": "Single-item triage",
    "properties": {
        "urgency": "high",
        "urgency_reason": "Mobile app crash during login affects iOS users.",
        "category": "incident",
        "category_reason": "Outage-style failure report.",
        "sentiment": "negative",
        "sentiment_reason": "Users are blocked from signing in.",
        "confidence": 0.8,
        "evidence_refs": ["rt-v1-018"],
    },
}


def test_instance_prompt_has_enums_not_json_schema_dump() -> None:
    text = instance_schema_prompt(TriagePayload, allowed_ids=["triage-v1-001"])
    assert "NOT a JSON Schema" in text
    assert 'Do not wrap fields under "properties"' in text
    assert "critical" in text and "high" in text and "medium" in text and "low" in text
    assert "incident" in text and "follow_up" in text
    assert "negative" in text and "positive" in text
    assert "confidence" in text and "0 and 1" in text
    assert "triage-v1-001" in text
    assert "evidence_refs" in text
    # Must not dump raw JSON Schema type maps
    assert "'type': 'string'" not in text
    assert '"type": "object"' not in text
    assert "$ref" not in text
    assert schema_prompt_fragment(TriagePayload) == instance_schema_prompt(TriagePayload)


def test_instance_prompt_without_allowed_ids_points_at_untrusted() -> None:
    text = instance_schema_prompt(TriagePayload)
    assert "UNTRUSTED" in text
    assert "id=" in text


def test_unwrap_mistral_schema_echo() -> None:
    out = unwrap_schema_echo(_MISTRAL_SCHEMA_ECHO)
    assert out["urgency"] == "high"
    assert out["evidence_refs"] == ["rt-v1-018"]
    assert "description" not in out
    assert "properties" not in out


def test_unwrap_leaves_real_json_schema_alone() -> None:
    schemaish = {
        "type": "object",
        "properties": {
            "urgency": {"type": "string", "enum": ["high", "low"]},
            "confidence": {"type": "number"},
        },
    }
    assert unwrap_schema_echo(schemaish) is schemaish


def test_unwrap_leaves_flat_instance_alone() -> None:
    flat = {
        "urgency": "high",
        "urgency_reason": "x",
        "category": "incident",
        "category_reason": "y",
        "sentiment": "negative",
        "sentiment_reason": "z",
        "confidence": 0.5,
        "evidence_refs": ["triage-v1-001"],
    }
    assert unwrap_schema_echo(flat) is flat


def test_try_parse_accepts_mistral_schema_echo() -> None:
    text = json.dumps(_MISTRAL_SCHEMA_ECHO)
    parsed, err, cls = BudgetAwareGateway._try_parse(TriagePayload, text)
    assert cls == "ok"
    assert err == ""
    assert parsed is not None
    assert parsed.urgency == "high"
    assert parsed.evidence_refs == ["rt-v1-018"]
