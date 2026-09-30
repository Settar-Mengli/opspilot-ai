"""Tests for live metrics honesty (D-LIVE-2..5,8..11)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from opspilot.evals.live import (
    HARNESS_VERSION,
    failed_case_ids,
    merge_live_results,
    recompute_live_metrics,
    run_live,
)
from opspilot.llm.providers.fake import FakeProvider
from opspilot.llm.schemas.triage import TriagePayload
from opspilot.llm.types import Message, TaskName


@pytest.fixture
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)


def _valid_payload(item_id: str) -> str:
    return json.dumps(
        {
            "urgency": "low",
            "urgency_reason": "unit test reason",
            "category": "other",
            "category_reason": "unit test reason",
            "sentiment": "neutral",
            "sentiment_reason": "unit test reason",
            "confidence": 0.5,
            "evidence_refs": [item_id],
        }
    )


@pytest.mark.usefixtures("allow_llm")
def test_empty_evidence_refs_is_grounding_failed(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "50")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")

    def responder(
        task: TaskName,
        messages: list[Message],
        schema: type[TriagePayload],
        repair_hint: str | None,
    ) -> str:
        del task, messages, schema, repair_hint
        return json.dumps(
            {
                "urgency": "low",
                "urgency_reason": "ok",
                "category": "other",
                "category_reason": "ok",
                "sentiment": "neutral",
                "sentiment_reason": "ok",
                "confidence": 0.5,
                "evidence_refs": [],
            }
        )

    fake = FakeProvider(name="gemini", json_responder=responder)  # type: ignore[arg-type]
    report = run_live(
        provider_name="gemini",
        session=db_session,
        providers=[fake],
        triage_limit=1,
        redteam_limit=0,
        inter_case_sleep_s=0.0,
    )
    assert report["cases"][0]["status"] == "grounding_failed"
    assert report["accepted"] == 0


@pytest.mark.usefixtures("allow_llm")
def test_repair_at_most_one_per_case(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "50")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    calls = {"n": 0}

    def responder(
        task: TaskName,
        messages: list[Message],
        schema: type[TriagePayload],
        repair_hint: str | None,
    ) -> str:
        del task, schema
        calls["n"] += 1
        if repair_hint is None and calls["n"] == 1:
            return "{}"
        item_id = "triage-v1-001"
        for msg in messages:
            if "UNTRUSTED" in msg.content and 'id="' in msg.content:
                item_id = msg.content.split('id="', 1)[1].split('"', 1)[0]
                break
        return _valid_payload(item_id)

    fake = FakeProvider(name="gemini", json_responder=responder)  # type: ignore[arg-type]
    report = run_live(
        provider_name="gemini",
        session=db_session,
        providers=[fake],
        triage_limit=1,
        redteam_limit=0,
        inter_case_sleep_s=0.0,
    )
    assert report["repair_events"] == 1
    assert report["repair_pct"] <= 1.0
    assert report["cases"][0].get("repaired") is True
    assert report["harness_version"] == HARNESS_VERSION
    assert "model" in report and "json_mode" in report and "max_tokens" in report
    assert report["triage_macro_f1_n"] == 1


def test_merge_never_keeps_stale_f1_when_preds_complete() -> None:
    base = {
        "provider": "groq",
        "triage_macro_f1": 0.11,
        "cases": [
            {"id": "triage-v1-001", "status": "accepted"},  # missing pred
            {
                "id": "triage-v1-002",
                "status": "accepted",
                "pred": {"urgency": "low", "category": "other", "sentiment": "neutral"},
            },
        ],
        "redteam": [],
    }
    patch = {
        "created_utc": "2026-09-30T00:00:00Z",
        "cases": [
            {
                "id": "triage-v1-001",
                "status": "accepted",
                "pred": {"urgency": "critical", "category": "incident", "sentiment": "negative"},
                "repaired": False,
            }
        ],
        "redteam": [],
        "repair_events": 0,
    }
    merged = merge_live_results(base, patch)
    assert merged["triage_macro_f1"] != 0.11
    assert merged["missing_pred_ids"] == []
    assert merged["triage_macro_f1_n"] == 2


def test_failed_case_ids_includes_accepted_without_pred() -> None:
    result = {
        "cases": [
            {"id": "triage-v1-001", "status": "accepted"},
            {
                "id": "triage-v1-002",
                "status": "accepted",
                "pred": {"urgency": "low", "category": "other", "sentiment": "neutral"},
            },
            {"id": "triage-v1-003", "status": "LlmSchemaError"},
        ],
        "redteam": [],
    }
    ids = failed_case_ids(result)
    assert ids == {"triage-v1-001", "triage-v1-003"}


def test_recompute_live_metrics_from_fixture(tmp_path: Path) -> None:
    payload = {
        "provider": "gemini",
        "cases": [
            {
                "id": "triage-v1-001",
                "status": "accepted",
                "pred": {"urgency": "critical", "category": "incident", "sentiment": "negative"},
                "repaired": False,
            }
        ],
        "redteam": [
            {
                "id": "rt-v1-001",
                "status": "grounding_failed",
                "attack_class": "delimiter_breakout",
                "attack_targets": ["delimiter_leak"],
            }
        ],
        "triage_macro_f1": 0.0,
    }
    out = recompute_live_metrics(payload)
    assert out["validity_n"]["accepted"] == 1
    assert out["validity_n"]["attempts"] == 2
    assert out["asr"]["blocked_by_defenses"] == 1
    assert out["asr"]["accepted"] == 0
    assert out["asr"]["rate"] is None
    assert out["triage_macro_f1_n"] == 1
    assert out["repair_events"] == 0
