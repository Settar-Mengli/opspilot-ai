"""emit_llm_span free-text meta strip under GITHUB_ACTIONS (dual-branch pins)."""

from __future__ import annotations

import json

import pytest

from opspilot.obs import tracing as tracing_mod
from opspilot.obs.tracing import LlmSpanAttrs, emit_llm_span


def _emit_and_parse(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    recorded: list[str] = []

    def _capture(msg: str, *args: object, **_kwargs: object) -> None:
        recorded.append(msg % args if args else msg)

    monkeypatch.setattr(tracing_mod.logger, "info", _capture)
    emit_llm_span(
        LlmSpanAttrs(
            task="ask",
            provider="fake",
            model="m",
            status="error",
            meta={
                "status_code": 500,
                "provider_error": "boom detail",
                "output_head": "partial output",
                "validation_error": "bad json",
                "error_class": "ValueError",
                "output_len": 12,
            },
        )
    )
    assert recorded
    line = recorded[0]
    assert line.startswith("llm.span ")
    return json.loads(line.removeprefix("llm.span "))


def test_emit_llm_span_keeps_free_text_meta_when_gha_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    payload = _emit_and_parse(monkeypatch)
    meta = payload["opspilot.meta"]
    assert isinstance(meta, dict)
    assert meta["provider_error"] == "boom detail"
    assert meta["output_head"] == "partial output"
    assert meta["validation_error"] == "bad json"
    assert meta["status_code"] == 500
    assert meta["error_class"] == "ValueError"
    assert meta["output_len"] == 12


def test_emit_llm_span_strips_free_text_meta_when_gha_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("CI", "true")
    payload = _emit_and_parse(monkeypatch)
    meta = payload["opspilot.meta"]
    assert isinstance(meta, dict)
    assert "provider_error" not in meta
    assert "output_head" not in meta
    assert "validation_error" not in meta
    assert meta["status_code"] == 500
    assert meta["error_class"] == "ValueError"
    assert meta["output_len"] == 12
