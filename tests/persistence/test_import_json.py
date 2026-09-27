"""X5 importer idempotency tests (sample + committed history fixture)."""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.jobs.import_json import (
    import_history_runs,
    import_sample_file,
    run_import,
    upsert_run_from_metadata,
)
from opspilot.persistence.models import RunArtifactRow, RunRow, WorkItemRow

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = PROJECT_ROOT / "data" / "raw" / "sample_input.json"
FIXTURE_HISTORY = PROJECT_ROOT / "tests" / "fixtures" / "history"


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


def test_history_import_idempotent_fixture(db_session: Session, tmp_path: Path, test_database_url: str) -> None:
    import_sample_file(db_session, SAMPLE_PATH)
    db_session.commit()

    history_root = tmp_path / "history"
    shutil.copytree(FIXTURE_HISTORY, history_root)

    first = import_history_runs(db_session, history_root)
    db_session.commit()
    count1 = db_session.scalar(select(func.count()).select_from(RunRow))
    assert first == 1
    assert count1 == 1

    second = import_history_runs(db_session, history_root)
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


def test_upsert_run_skips_artifact_path_escape(db_session: Session, tmp_path: Path) -> None:
    """F-06: artifact filenames must stay inside run_dir (no ../ escape)."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    safe = run_dir / "safe.txt"
    safe.write_text("inside", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("leaked", encoding="utf-8")

    metadata = {
        "run_id": "run-jail-001",
        "status": "success",
        "artifacts": {
            "safe_doc": "safe.txt",
            "escape": "../outside.txt",
        },
    }
    upsert_run_from_metadata(db_session, metadata, run_dir)
    db_session.commit()

    arts = list(db_session.scalars(select(RunArtifactRow).where(RunArtifactRow.run_id == "run-jail-001")))
    names = {a.name for a in arts}
    assert names == {"safe_doc"}
    assert arts[0].content == "inside"
