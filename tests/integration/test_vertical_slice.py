import json
import re
from pathlib import Path

from opspilot.pipeline.run_daily_ops import run_daily_ops

FIXTURE_PATH = Path("tests/fixtures/sample_input.json")


def test_vertical_slice_generates_all_outputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    result_paths = run_daily_ops(str(FIXTURE_PATH), str(output_dir), "2026-05-29")

    triage_file = Path(result_paths["triage_results"])
    action_file = Path(result_paths["action_items"])
    response_file = Path(result_paths["suggested_responses"])
    briefing_file = Path(result_paths["daily_briefing"])

    assert triage_file.exists()
    assert action_file.exists()
    assert response_file.exists()
    assert briefing_file.exists()

    triage_payload = json.loads(triage_file.read_text(encoding="utf-8"))
    response_payload = json.loads(response_file.read_text(encoding="utf-8"))
    briefing_text = briefing_file.read_text(encoding="utf-8")

    fixture_payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert len(triage_payload) == len(fixture_payload)
    assert len(triage_payload) == 6
    assert any(record["urgency"] == "critical" for record in triage_payload)
    assert all("urgency_reason" in record for record in triage_payload)
    assert all("category_reason" in record for record in triage_payload)
    assert all("sentiment_reason" in record for record in triage_payload)
    assert len(response_payload) == len(fixture_payload)
    assert "Total Work Items" in briefing_text
    assert "Urgency Mix" in briefing_text
    assert "Top Priorities" in briefing_text
    assert "- WI-001: Production outage in checkout service" in briefing_text


def test_pipeline_creates_immutable_run_history_with_metadata(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    run_daily_ops(str(FIXTURE_PATH), str(output_dir), "2026-05-29")

    history_root = tmp_path / "history" / "runs"
    run_dirs = [path for path in history_root.rglob("run-*") if path.is_dir()]

    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert re.match(r"^run-\d{8}-\d{6}-\d{3}(?:-\d{2})?$", run_dir.name)

    assert (run_dir / "triage_results.json").exists()
    assert (run_dir / "action_items.json").exists()
    assert (run_dir / "suggested_responses.json").exists()
    assert (run_dir / "daily_briefing.txt").exists()

    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    expected_fields = {
        "run_id",
        "started_at",
        "finished_at",
        "duration_ms",
        "status",
        "input_file",
        "output_dir",
        "history_dir",
        "item_count",
        "triage_count",
        "action_count",
        "suggested_response_count",
        "artifacts",
        "error",
    }

    assert expected_fields.issubset(metadata.keys())
    assert metadata["status"] == "success"
    assert metadata["error"] is None
    assert metadata["run_id"] == run_dir.name

    artifact_names = metadata["artifacts"]
    assert artifact_names["triage_results"] == "triage_results.json"
    assert artifact_names["action_items"] == "action_items.json"
    assert artifact_names["suggested_responses"] == "suggested_responses.json"
    assert artifact_names["daily_briefing"] == "daily_briefing.txt"


def test_two_runs_create_distinct_run_history_directories(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"

    run_daily_ops(str(FIXTURE_PATH), str(output_dir), "2026-05-29")
    run_daily_ops(str(FIXTURE_PATH), str(output_dir), "2026-05-29")

    history_root = tmp_path / "history" / "runs"
    run_dirs = sorted(path for path in history_root.rglob("run-*") if path.is_dir())

    assert len(run_dirs) == 2
    assert run_dirs[0].name != run_dirs[1].name
    assert (run_dirs[0] / "run.json").exists()
    assert (run_dirs[1] / "run.json").exists()


def test_pipeline_still_writes_latest_output_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"

    run_daily_ops(str(FIXTURE_PATH), str(output_dir), "2026-05-29")

    assert (output_dir / "triage_results.json").exists()
    assert (output_dir / "action_items.json").exists()
    assert (output_dir / "suggested_responses.json").exists()
    assert (output_dir / "daily_briefing.txt").exists()
