import json
from pathlib import Path

from opspilot.history.run_history import find_previous_run_id
from opspilot.models.schemas import ActionItem, TriageRecord, WorkItem
from opspilot.nlp.briefing_generator import generate_daily_briefing


def _write_triage_artifact(runs_root: Path, run_id: str, payload: list[dict[str, object]]) -> None:
    run_dir = runs_root / "2026" / "05" / "30" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "triage_results.json").write_text(json.dumps(payload), encoding="utf-8")
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "started_at": "2026-05-30T03:00:00Z",
                "finished_at": "2026-05-30T03:01:00Z",
                "status": "success",
                "artifacts": {"triage_results": "triage_results.json"},
            }
        ),
        encoding="utf-8",
    )


def _write_run_metadata_only(runs_root: Path, run_id: str) -> None:
    run_dir = runs_root / "2026" / "05" / "30" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "started_at": "2026-05-30T03:00:00Z",
                "finished_at": "2026-05-30T03:01:00Z",
                "status": "success",
                "artifacts": {"triage_results": "triage_results.json"},
            }
        ),
        encoding="utf-8",
    )


def _sample_work_items() -> list[WorkItem]:
    return [
        WorkItem(
            id="WI-001",
            source_type="email",
            subject_or_title="Production outage",
            body_or_description="Checkout is down",
            sender_or_requester="ops@local",
            received_at="2026-05-30T03:00:00Z",
            tags=[],
        )
    ]


def _sample_action_items() -> list[ActionItem]:
    return [
        ActionItem(
            work_item_id="WI-001",
            summary="Restore checkout service",
            owner="IT Ops",
            deadline="EOD",
            explicit_ask="please",
        )
    ]


def test_find_previous_run_id_returns_none_when_no_previous(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    _write_triage_artifact(runs_root, "run-20260530-040000-000", [])

    previous = find_previous_run_id("run-20260530-040000-000", runs_root)

    assert previous is None


def test_find_previous_run_id_returns_immediately_previous_from_multiple(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    _write_triage_artifact(runs_root, "run-20260530-033000-100", [])
    _write_triage_artifact(runs_root, "run-20260530-034000-200", [])
    _write_triage_artifact(runs_root, "run-20260530-035000-300", [])
    _write_triage_artifact(runs_root, "run-20260530-041000-400", [])

    previous = find_previous_run_id("run-20260530-035000-300", runs_root)

    assert previous == "run-20260530-034000-200"


def test_generate_daily_briefing_renders_since_last_run_table(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    previous_run_id = "run-20260530-033000-100"
    current_run_id = "run-20260530-034000-200"

    _write_triage_artifact(
        runs_root,
        previous_run_id,
        [
            {"id": "A", "urgency": "critical"},
            {"id": "B", "urgency": "high"},
            {"id": "C", "urgency": "high"},
        ],
    )
    _write_triage_artifact(runs_root, current_run_id, [])

    triage_records = [
        TriageRecord("WI-001", "critical", "", "incident", "", "negative", ""),
        TriageRecord("WI-002", "critical", "", "incident", "", "negative", ""),
        TriageRecord("WI-003", "low", "", "request", "", "neutral", ""),
    ]

    briefing = generate_daily_briefing(
        run_date="2026-05-30",
        triage_records=triage_records,
        action_items=_sample_action_items(),
        work_items=_sample_work_items(),
        current_run_id=current_run_id,
        runs_root=runs_root,
    )

    assert "## Since Last Run" in briefing
    assert f"_Compared to {previous_run_id}_" in briefing
    assert "| Priority | Previous | Current | Change |" in briefing
    assert "| Critical | 1 | 2 | +1 |" in briefing
    assert "| High | 2 | 0 | -2 |" in briefing
    assert "| Medium | 0 | 0 | 0 |" in briefing
    assert "| Low | 0 | 1 | +1 |" in briefing
    assert "## Recent Trend (Last 7 Runs)" in briefing
    assert f"- {current_run_id}: high_risk=2" in briefing
    assert f"- {previous_run_id}: high_risk=3" in briefing
    assert "Net change across 2 runs: -1." in briefing


def test_generate_daily_briefing_falls_back_when_no_previous_run(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    current_run_id = "run-20260530-034000-200"
    _write_triage_artifact(runs_root, current_run_id, [])

    briefing = generate_daily_briefing(
        run_date="2026-05-30",
        triage_records=[TriageRecord("WI-001", "medium", "", "request", "", "neutral", "")],
        action_items=_sample_action_items(),
        work_items=_sample_work_items(),
        current_run_id=current_run_id,
        runs_root=runs_root,
    )

    assert "## Since Last Run" in briefing
    assert "No previous run available for comparison." in briefing
    assert "## Recent Trend (Last 7 Runs)" in briefing
    assert f"- {current_run_id}: high_risk=0" in briefing
    assert "Only current run available; additional runs are needed for trend comparison." in briefing


def test_generate_daily_briefing_recent_trend_limits_to_last_7_runs(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    current_run_id = "run-20260530-038000-800"

    previous_runs = [
        "run-20260530-037000-700",
        "run-20260530-036000-600",
        "run-20260530-035000-500",
        "run-20260530-034000-400",
        "run-20260530-033000-300",
        "run-20260530-032000-200",
        "run-20260530-031000-100",
    ]
    for run_id in previous_runs:
        _write_triage_artifact(runs_root, run_id, [{"id": "A", "urgency": "high"}])

    briefing = generate_daily_briefing(
        run_date="2026-05-30",
        triage_records=[
            TriageRecord("WI-001", "critical", "", "incident", "", "negative", ""),
            TriageRecord("WI-002", "high", "", "incident", "", "negative", ""),
        ],
        action_items=_sample_action_items(),
        work_items=_sample_work_items(),
        current_run_id=current_run_id,
        runs_root=runs_root,
    )

    assert "## Recent Trend (Last 7 Runs)" in briefing
    assert f"- {current_run_id}: high_risk=2" in briefing
    assert "- run-20260530-037000-700: high_risk=1" in briefing
    assert "- run-20260530-032000-200: high_risk=1" in briefing
    assert "run-20260530-031000-100" not in briefing
    assert "Net change across 7 runs: +1." in briefing


def test_generate_daily_briefing_handles_missing_previous_triage_artifact(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    current_run_id = "run-20260530-034000-200"
    previous_run_id = "run-20260530-033000-100"

    _write_run_metadata_only(runs_root, previous_run_id)
    _write_triage_artifact(runs_root, current_run_id, [])

    briefing = generate_daily_briefing(
        run_date="2026-05-30",
        triage_records=[TriageRecord("WI-001", "high", "", "incident", "", "negative", "")],
        action_items=_sample_action_items(),
        work_items=_sample_work_items(),
        current_run_id=current_run_id,
        runs_root=runs_root,
    )

    assert "## Since Last Run" in briefing
    assert "No previous run available for comparison." in briefing
    assert "## Recent Trend (Last 7 Runs)" in briefing
    assert f"- {current_run_id}: high_risk=1" in briefing
    assert "Only current run available; additional runs are needed for trend comparison." in briefing


def test_generate_daily_briefing_trend_skips_malformed_historical_triage_artifact(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    current_run_id = "run-20260530-036000-300"
    malformed_run_id = "run-20260530-035000-200"
    valid_run_id = "run-20260530-034000-100"

    _write_triage_artifact(runs_root, current_run_id, [])
    _write_run_metadata_only(runs_root, malformed_run_id)
    malformed_path = runs_root / "2026" / "05" / "30" / malformed_run_id / "triage_results.json"
    malformed_path.write_text("{ not-json", encoding="utf-8")
    _write_triage_artifact(runs_root, valid_run_id, [{"id": "A", "urgency": "high"}])

    briefing = generate_daily_briefing(
        run_date="2026-05-30",
        triage_records=[TriageRecord("WI-001", "critical", "", "incident", "", "negative", "")],
        action_items=_sample_action_items(),
        work_items=_sample_work_items(),
        current_run_id=current_run_id,
        runs_root=runs_root,
    )

    assert "## Recent Trend (Last 7 Runs)" in briefing
    assert f"- {current_run_id}: high_risk=1" in briefing
    assert f"- {valid_run_id}: high_risk=1" in briefing
    assert malformed_run_id not in briefing
    assert "Net change across 2 runs: 0." in briefing
