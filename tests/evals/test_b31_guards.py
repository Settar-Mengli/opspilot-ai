"""Tests for B3.1 live eval guards (checkpoint, selection, local DB, ceiling)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from opspilot.evals.live import (
    LiveCeilingReached,
    LiveEvalError,
    missing_case_ids_from_artifact,
    require_local_database_url,
    run_live,
)
from opspilot.evals.report import write_eval_json
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


def _responder(
    task: TaskName,
    messages: list[Message],
    schema: type[TriagePayload],
    repair_hint: str | None,
) -> str:
    del task, schema, repair_hint
    item_id = "triage-v1-001"
    for msg in messages:
        if "UNTRUSTED" in msg.content and 'id="' in msg.content:
            item_id = msg.content.split('id="', 1)[1].split('"', 1)[0]
            break
    return _valid_payload(item_id)


@pytest.mark.usefixtures("allow_llm")
def test_checkpoint_preserves_rows_on_mid_run_error(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "50")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    out = tmp_path / "partial.json"
    calls = {"n": 0}

    def boom_after_two(
        task: TaskName,
        messages: list[Message],
        schema: type[TriagePayload],
        repair_hint: str | None,
    ) -> str:
        calls["n"] += 1
        if calls["n"] > 2:
            raise RuntimeError("injected mid-run failure")
        return _responder(task, messages, schema, repair_hint)

    fake = FakeProvider(name="gemini", json_responder=boom_after_two)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="injected"):
        run_live(
            provider_name="gemini",
            session=db_session,
            providers=[fake],
            triage_limit=5,
            redteam_limit=0,
            inter_case_sleep_s=0.0,
            checkpoint_path=out,
        )
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["partial"] is True
    assert len(data["cases"]) >= 1


@pytest.mark.usefixtures("allow_llm")
def test_missing_from_selects_remainder_ids() -> None:
    artifact = {
        "cases": [{"id": "triage-v1-001", "status": "accepted"}, {"id": "triage-v1-002", "status": "accepted"}],
        "redteam": [],
    }
    missing = missing_case_ids_from_artifact(artifact, suite="triage")
    assert "triage-v1-001" not in missing
    assert "triage-v1-003" in missing
    assert "rt-v1-001" not in missing


@pytest.mark.usefixtures("allow_llm")
def test_suite_redteam_only(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "50")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    fake = FakeProvider(name="gemini", json_responder=_responder)  # type: ignore[arg-type]
    report = run_live(
        provider_name="gemini",
        session=db_session,
        providers=[fake],
        suite="redteam",
        redteam_limit=2,
        inter_case_sleep_s=0.0,
    )
    assert report["n_triage"] == 0
    assert report["n_redteam"] == 2


@pytest.mark.usefixtures("allow_llm")
def test_require_local_database_refuses_neon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://u:p@ep-test.us-east-1.aws.neon.tech/neondb",
    )
    monkeypatch.delenv("OPSPILOT_LIVE_ALLOW_NONLOCAL_DB", raising=False)
    with pytest.raises(LiveEvalError, match="non-local"):
        require_local_database_url()


@pytest.mark.usefixtures("allow_llm")
def test_require_local_database_allows_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://opspilot:opspilot@127.0.0.1:5432/opspilot")
    assert require_local_database_url() == "127.0.0.1"


@pytest.mark.usefixtures("allow_llm")
def test_max_requests_ceiling_checkpoints(db_session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "50")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    out = tmp_path / "ceil.json"
    fake = FakeProvider(name="gemini", json_responder=_responder)  # type: ignore[arg-type]
    with pytest.raises(LiveCeilingReached) as excinfo:
        run_live(
            provider_name="gemini",
            session=db_session,
            providers=[fake],
            triage_limit=10,
            redteam_limit=0,
            inter_case_sleep_s=0.0,
            checkpoint_path=out,
            max_requests=1,
        )
    partial = excinfo.value.partial
    assert partial["run_status"] == "ceiling_reached"
    assert partial["partial"] is True
    assert out.is_file()
    assert len(partial["cases"]) >= 1


@pytest.mark.usefixtures("allow_llm")
def test_on_after_case_commit_persists_budget(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "50")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    commits = {"n": 0}

    def _commit() -> None:
        db_session.commit()
        commits["n"] += 1

    fake = FakeProvider(name="gemini", json_responder=_responder)  # type: ignore[arg-type]
    run_live(
        provider_name="gemini",
        session=db_session,
        providers=[fake],
        triage_limit=2,
        redteam_limit=0,
        inter_case_sleep_s=0.0,
        on_after_case=_commit,
    )
    assert commits["n"] == 2
    row = db_session.execute(
        text("SELECT req_count FROM llm_budget_counters WHERE provider = 'gemini' ORDER BY day_utc DESC LIMIT 1")
    ).first()
    assert row is not None
    assert int(row[0]) >= 2


def test_atomic_write_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "x.json"
    write_eval_json(path, {"partial": True, "n": 1})
    write_eval_json(path, {"partial": False, "n": 2})
    assert json.loads(path.read_text(encoding="utf-8")) == {"n": 2, "partial": False}
