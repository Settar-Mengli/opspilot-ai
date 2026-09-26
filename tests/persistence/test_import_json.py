"""X5 importer idempotency tests (sample + history)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.jobs.import_json import import_history_runs, import_sample_file, run_import
from opspilot.persistence.models import RunRow, WorkItemRow

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = PROJECT_ROOT / "data" / "raw" / "sample_input.json"
HISTORY_ROOT = PROJECT_ROOT / "data" / "history" / "runs"


def test_sample_import_idempotent(db_session: Session, test_database_url: str) -> None:
    assert SAMPLE_PATH.is_file()
    first = import_sample_file(db_session, SAMPLE_PATH)
    db_session.commit()
    count_after_first = db_session.scalar(select(func.count()).select_from(WorkItemRow))
    assert first > 0
    assert count_after_first == first

    second = import_sample_file(db_session, SAMPLE_PATH)
    db_session.commit()
    count_after_second = db_session.scalar(select(func.count()).select_from(WorkItemRow))
    assert second == first
    assert count_after_second == count_after_first


def test_history_import_idempotent_synthetic(db_session: Session, tmp_path: Path, test_database_url: str) -> None:
    # Seed a work item so triage FK can attach.
    import_sample_file(
        db_session,
        SAMPLE_PATH,
    )
    db_session.commit()

    run_id = "run-20260530-120000-001"
    run_dir = tmp_path / "2026" / "05" / "30" / run_id
    run_dir.mkdir(parents=True)
    triage = [
        {
            "id": "WI-001",
            "urgency": "high",
            "urgency_reason": "synthetic",
            "category": "incident",
            "category_reason": "synthetic",
            "sentiment": "negative",
            "sentiment_reason": "synthetic",
        }
    ]
    (run_dir / "triage_results.json").write_text(json.dumps(triage), encoding="utf-8")
    (run_dir / "daily_briefing.txt").write_text("OpsPilot AI Daily Executive Briefing\n", encoding="utf-8")
    metadata = {
        "run_id": run_id,
        "started_at": "2026-05-30T12:00:00Z",
        "finished_at": "2026-05-30T12:00:01Z",
        "duration_ms": 1000,
        "status": "success",
        "input_file": "sample_input.json",
        "item_count": 1,
        "triage_count": 1,
        "artifacts": {
            "triage_results": "triage_results.json",
            "daily_briefing": "daily_briefing.txt",
        },
    }
    (run_dir / "run.json").write_text(json.dumps(metadata), encoding="utf-8")

    first = import_history_runs(db_session, tmp_path)
    db_session.commit()
    count1 = db_session.scalar(select(func.count()).select_from(RunRow))
    assert first == 1
    assert count1 == 1

    second = import_history_runs(db_session, tmp_path)
    db_session.commit()
    count2 = db_session.scalar(select(func.count()).select_from(RunRow))
    assert second == 1
    assert count2 == count1


def test_history_import_real_when_present(db_session: Session, test_database_url: str) -> None:
    if not HISTORY_ROOT.is_dir():
        pytest.skip("data/history/runs not present")
    run_files = list(HISTORY_ROOT.rglob("run.json"))
    if not run_files:
        pytest.skip("no history run.json files")

    # Sample first so triage FKs can resolve for known WI ids.
    if SAMPLE_PATH.is_file():
        import_sample_file(db_session, SAMPLE_PATH)
        db_session.commit()

    first = import_history_runs(db_session, HISTORY_ROOT)
    db_session.commit()
    count1 = db_session.scalar(select(func.count()).select_from(RunRow))
    assert first > 0
    assert count1 == first

    second = import_history_runs(db_session, HISTORY_ROOT)
    db_session.commit()
    count2 = db_session.scalar(select(func.count()).select_from(RunRow))
    assert second == first
    assert count2 == count1


def test_run_import_cli_helper_round_trip(test_database_url: str) -> None:
    stats1 = run_import(
        sample_path=SAMPLE_PATH,
        history_root=None,
        database_url=test_database_url,
    )
    stats2 = run_import(
        sample_path=SAMPLE_PATH,
        history_root=None,
        database_url=test_database_url,
    )
    assert stats1["work_item_count"] == stats2["work_item_count"]
    assert stats1["work_item_count"] > 0
