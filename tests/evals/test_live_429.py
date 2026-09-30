"""Hermetic 429 retry + RPM pacing tests for live evals."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from opspilot.evals.live import (
    MAX_429_RETRIES,
    backoff_sleep_s,
    failed_case_ids,
    merge_live_results,
    provider_min_interval_s,
    run_live,
)
from opspilot.llm.providers.fake import FakeProvider
from opspilot.llm.types import AttemptStatus, ProviderResult


@pytest.fixture
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)


def _valid(item_id: str = "triage-v1-001") -> str:
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


def test_groq_min_interval_is_at_least_2_5() -> None:
    assert provider_min_interval_s("groq") >= 2.5


def test_backoff_prefers_retry_after_capped_at_60() -> None:
    assert backoff_sleep_s(attempt_index=0, retry_after_s=3.0) == 3.0
    assert backoff_sleep_s(attempt_index=0, retry_after_s=120.0) == 60.0
    assert backoff_sleep_s(attempt_index=2, retry_after_s=None) == 4.0
    assert backoff_sleep_s(attempt_index=10, retry_after_s=None) == 60.0


@pytest.mark.usefixtures("allow_llm")
def test_live_retries_429_then_accepts(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_REQ_DAY", "50")
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_TOK_DAY", "500000")
    sleeps: list[float] = []

    def sleeper(seconds: float) -> None:
        sleeps.append(seconds)

    # First complete_json path: RATE_LIMITED → exhausted 429; live retries; then SUCCESS.
    # Gateway may also attempt force_json_object on schema errors — use RATE_LIMITED only.
    results = [
        ProviderResult(
            status=AttemptStatus.RATE_LIMITED,
            error_code="429",
            retry_after_s=1.25,
            model="fake",
        ),
        ProviderResult(status=AttemptStatus.SUCCESS, text=_valid(), model="fake"),
    ]
    fake = FakeProvider(name="groq", json_results=results)
    report = run_live(
        provider_name="groq",
        session=db_session,
        providers=[fake],
        triage_limit=1,
        redteam_limit=0,
        inter_case_sleep_s=0.0,
        sleeper=sleeper,
    )
    assert report["accepted"] == 1
    assert report["cases"][0]["status"] == "accepted"
    assert report["cases"][0]["pred"]["urgency"] == "low"
    # One backoff sleep for the 429 retry (Retry-After=1.25); pacing disabled via inter_case_sleep_s=0.
    assert any(abs(s - 1.25) < 1e-6 for s in sleeps)


@pytest.mark.usefixtures("allow_llm")
def test_live_gives_up_after_max_429_retries(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_REQ_DAY", "50")
    monkeypatch.setenv("OPSPILOT_BUDGET_GROQ_TOK_DAY", "500000")
    sleeps: list[float] = []

    limited = ProviderResult(
        status=AttemptStatus.RATE_LIMITED,
        error_code="429",
        retry_after_s=0.5,
        model="fake",
    )
    # Enough 429s for initial + MAX_429_RETRIES retries (each attempt one provider call).
    fake = FakeProvider(name="groq", json_results=[limited] * (MAX_429_RETRIES + 2))
    report = run_live(
        provider_name="groq",
        session=db_session,
        providers=[fake],
        triage_limit=1,
        redteam_limit=0,
        inter_case_sleep_s=0.0,
        sleeper=sleeps.append,
    )
    assert report["accepted"] == 0
    assert report["cases"][0]["status"] == "429"
    assert len(sleeps) == MAX_429_RETRIES


def test_merge_and_failed_ids() -> None:
    base = {
        "provider": "groq",
        "cases": [
            {
                "id": "triage-v1-001",
                "status": "accepted",
                "pred": {"urgency": "critical", "category": "incident", "sentiment": "negative"},
            },
            {"id": "triage-v1-002", "status": "429"},
        ],
        "redteam": [{"id": "rt-v1-001", "status": "429", "attack_class": "x", "attack_targets": []}],
        "repair_events": 0,
        "rate_limit_events": 2,
        "triage_macro_f1": 0.5,
    }
    assert failed_case_ids(base) == {"triage-v1-002", "rt-v1-001"}
    patch = {
        "created_utc": "2026-09-30T00:00:00Z",
        "cases": [
            {
                "id": "triage-v1-002",
                "status": "accepted",
                "pred": {"urgency": "low", "category": "other", "sentiment": "positive"},
            }
        ],
        "redteam": [
            {
                "id": "rt-v1-001",
                "status": "accepted",
                "attack_class": "x",
                "attack_targets": [],
                "asr_success": False,
                "pred": {"urgency": "low", "category": "other", "sentiment": "neutral"},
                "repaired": False,
            }
        ],
        "repair_events": 0,
        "rate_limit_events": 1,
    }
    merged = merge_live_results(base, patch)
    assert merged["validity_pct"] == 1.0
    assert merged["asr"]["accepted"] == 1
    assert merged["asr"]["rate"] == 0.0
    assert failed_case_ids(merged) == set()
