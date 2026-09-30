"""Unit tests for LLM meta redaction (F-09 / F-04 aligned)."""

from __future__ import annotations

from opspilot.llm.meta_redact import http_error_meta, parse_failure_meta, redact_text, sanitize_meta


def test_redact_text_strips_email_and_keys() -> None:
    raw = "fail user@example.com key sk-ant-abcdefghijklmnop"
    out = redact_text(raw, max_chars=500)
    assert "user@example.com" not in out
    assert "sk-ant-abcdefghijklmnop" not in out
    assert "***" in out


def test_redact_text_bearer_space_form() -> None:
    raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc.def"
    out = redact_text(raw, max_chars=500)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc.def" not in out
    assert "***" in out


def test_redact_text_aiza_google_key() -> None:
    raw = "key=AIzaSyA-abcdefghijklmnopqrstuvwxyz012345"
    out = redact_text(raw, max_chars=500)
    assert "AIzaSyA-abcdefghijklmnopqrstuvwxyz012345" not in out
    assert "***" in out


def test_redact_text_cf_token() -> None:
    raw = "error cf_token=cfsecrettokenvalue12345 remaining"
    out = redact_text(raw, max_chars=500)
    assert "cfsecrettokenvalue12345" not in out
    assert "***" in out


def test_redact_text_password_passwd_secret_kv() -> None:
    raw = "password=hunter2 passwd=sekrit secret=topsecret remaining"
    out = redact_text(raw, max_chars=500)
    assert out == "*** *** *** remaining"


def test_redact_text_truncates() -> None:
    out = redact_text("x" * 1000, max_chars=50)
    assert len(out) == 50


def test_http_error_meta_truncates_and_redacts() -> None:
    body = '{"error":"bad schema","api_key":"sk-ant-abcdefghijklmnopqrstuvwxyz"}' + ("z" * 600)
    meta = http_error_meta(status_code=400, body=body)
    assert meta["status_code"] == 400
    assert len(meta["provider_error"]) <= 500
    assert "sk-ant-abcdefghijklmnopqrstuvwxyz" not in meta["provider_error"]
    assert "***" in meta["provider_error"]


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


def test_sanitize_meta_recursive_nested_secrets() -> None:
    safe = sanitize_meta(
        {
            "outer": {
                "password": "hunter2",
                "note": "Bearer eyJnested.jwt.token",
                "cf": "cf_token=cfnestedsecret99",
            },
            "list": [{"token": "abc123"}, {"msg": "AIzaSyNestedGoogleKey0123456789"}],
        }
    )
    assert safe["outer"]["password"] == "***"
    assert "eyJnested.jwt.token" not in safe["outer"]["note"]
    assert "cfnestedsecret99" not in safe["outer"]["cf"]
    assert safe["list"][0]["token"] == "***"
    assert "AIzaSyNestedGoogleKey0123456789" not in safe["list"][1]["msg"]
