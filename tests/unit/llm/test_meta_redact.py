"""Unit tests for LLM meta redaction (F-09 aligned)."""

from __future__ import annotations

from opspilot.llm.meta_redact import http_error_meta, parse_failure_meta, redact_text, sanitize_meta


def test_redact_text_strips_email_and_keys() -> None:
    raw = "fail user@example.com key sk-ant-abcdefghijklmnop bearer token=sekrit gsk_abcdefghijklmnop"
    out = redact_text(raw, max_chars=500)
    assert "user@example.com" not in out
    assert "sk-ant-" not in out or "***" in out
    assert "gsk_" not in out or "***" in out
    assert "***" in out


def test_redact_text_truncates() -> None:
    out = redact_text("x" * 1000, max_chars=50)
    assert len(out) == 50


def test_http_error_meta_truncates_and_redacts() -> None:
    body = '{"error":"bad schema","api_key":"sk-ant-abcdefghijklmnopqrstuvwxyz"}' + ("z" * 600)
    meta = http_error_meta(status_code=400, body=body)
    assert meta["status_code"] == 400
    assert len(meta["provider_error"]) <= 500
    assert "sk-ant-" not in meta["provider_error"] or "***" in meta["provider_error"]


def test_parse_failure_meta() -> None:
    meta = parse_failure_meta(
        error_class="schema_validation",
        validation_error="insights list empty",
        raw_output='{"intro":"hi","insights":[]}' + ("a" * 400),
    )
    assert meta["error_class"] == "schema_validation"
    assert meta["output_len"] > 300
    assert len(meta["output_head"]) <= 300


def test_sanitize_meta_redacts_secret_keys() -> None:
    safe = sanitize_meta({"api_key": "secret", "status_code": 400, "provider_error": "ok"})
    assert safe["api_key"] == "***"
    assert safe["status_code"] == 400
