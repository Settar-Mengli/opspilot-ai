import json
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
