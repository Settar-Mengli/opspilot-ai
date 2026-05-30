import os
import subprocess
import sys
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from opspilot.api.main import app

client = TestClient(app)


@pytest.fixture
def isolated_run_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    output_dir = tmp_path / "output"
    history_dir = tmp_path / "history" / "runs"
    monkeypatch.setattr("opspilot.api.main.API_OUTPUT_DIR", output_dir)
    monkeypatch.setattr("opspilot.api.main.HISTORY_RUNS_DIR", history_dir)
    return tmp_path

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.text == "ok"

def test_run_pipeline_success():
    resp = client.post("/run", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

def test_run_requires_date():
    resp = client.post("/run", json={"input_file": "sample_input.json"})
    assert resp.status_code == 422

def test_run_rejects_invalid_date_format():
    resp = client.post("/run", json={"input_file": "sample_input.json", "date": "29-05-2026"})
    assert resp.status_code == 422

def test_run_rejects_path_traversal():
    resp = client.post("/run", json={"input_file": "../sample_input.json", "date": "2026-05-29"})
    assert resp.status_code == 400

def test_run_timeout_returns_safe_error(monkeypatch: pytest.MonkeyPatch):
    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=kwargs.get("args", "opspilot"), timeout=30)

    monkeypatch.setattr("opspilot.api.main.subprocess.run", _timeout)
    resp = client.post("/run", json={"input_file": "sample_input.json", "date": "2026-05-29"})

    assert resp.status_code == 504
    payload = resp.json()
    assert isinstance(payload, dict)
    assert "detail" in payload
    assert payload["detail"]["error"] == "pipeline_timeout"
    assert payload["detail"]["message"] == "Pipeline run timed out."

def test_run_subprocess_failure_returns_safe_error(monkeypatch: pytest.MonkeyPatch):
    def _failed(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=2, cmd="opspilot", stderr="traceback: private detail")

    monkeypatch.setattr("opspilot.api.main.subprocess.run", _failed)
    resp = client.post("/run", json={"input_file": "sample_input.json", "date": "2026-05-29"})

    assert resp.status_code == 500
    payload = resp.json()
    assert isinstance(payload, dict)
    assert "detail" in payload
    assert payload["detail"]["error"] == "pipeline_failed"
    assert payload["detail"]["message"] == "Pipeline execution failed."
    assert "private detail" not in str(payload)

def test_get_briefing():
    resp = client.get("/briefing")
    assert resp.status_code == 200
    assert "OpsPilot AI Daily Executive Briefing" in resp.text

def test_get_triage():
    resp = client.get("/triage")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)
    assert payload
    assert "urgency_reason" in payload[0]
    categories = {record["category"] for record in payload}
    assert categories.issubset({"incident", "request", "admin", "follow_up", "other"})


def test_get_runs_returns_empty_list_when_history_missing(isolated_run_dirs: Path):
    resp = client.get("/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_runs_returns_metadata_after_pipeline_run(isolated_run_dirs: Path):
    run_resp = client.post("/run", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    assert run_resp.status_code == 200

    resp = client.get("/runs")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["status"] == "success"
    assert payload[0]["run_id"].startswith("run-")


def test_get_runs_metadata_is_sanitized_and_safe(isolated_run_dirs: Path):
    run_resp = client.post("/run", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    assert run_resp.status_code == 200

    resp = client.get("/runs")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)
    assert payload

    for item in payload:
        assert "output_dir" not in item
        assert "history_dir" not in item

        artifacts = item.get("artifacts")
        if isinstance(artifacts, dict):
            for name in artifacts.values():
                assert isinstance(name, str)
                assert name
                assert "/" not in name
                assert "\\" not in name
                assert ":" not in name


def test_get_runs_sorted_newest_first(isolated_run_dirs: Path):
    first = client.post("/run", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    second = client.post("/run", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    assert first.status_code == 200
    assert second.status_code == 200

    resp = client.get("/runs")
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) >= 2
    assert payload[0]["finished_at"] >= payload[1]["finished_at"]


def test_get_run_triage_returns_artifact_for_run(isolated_run_dirs: Path):
    run_resp = client.post("/run", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    assert run_resp.status_code == 200

    runs_resp = client.get("/runs")
    run_id = runs_resp.json()[0]["run_id"]

    triage_resp = client.get(f"/runs/{run_id}/triage")
    assert triage_resp.status_code == 200
    payload = triage_resp.json()
    assert isinstance(payload, list)
    assert payload
    assert "id" in payload[0]
    assert "urgency" in payload[0]


def test_get_run_briefing_returns_artifact_for_run(isolated_run_dirs: Path):
    run_resp = client.post("/run", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    assert run_resp.status_code == 200

    runs_resp = client.get("/runs")
    run_id = runs_resp.json()[0]["run_id"]

    briefing_resp = client.get(f"/runs/{run_id}/briefing")
    assert briefing_resp.status_code == 200
    assert "OpsPilot AI Daily Executive Briefing" in briefing_resp.text


def test_get_run_metadata_for_specific_run(isolated_run_dirs: Path):
    run_resp = client.post("/run", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    assert run_resp.status_code == 200

    runs_resp = client.get("/runs")
    run_id = runs_resp.json()[0]["run_id"]

    run_meta_resp = client.get(f"/runs/{run_id}")
    assert run_meta_resp.status_code == 200
    payload = run_meta_resp.json()
    assert payload["run_id"] == run_id
    assert payload["status"] == "success"


def test_get_run_metadata_is_sanitized_and_safe(isolated_run_dirs: Path):
    run_resp = client.post("/run", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    assert run_resp.status_code == 200

    runs_resp = client.get("/runs")
    run_id = runs_resp.json()[0]["run_id"]

    run_meta_resp = client.get(f"/runs/{run_id}")
    assert run_meta_resp.status_code == 200
    payload = run_meta_resp.json()

    assert "output_dir" not in payload
    assert "history_dir" not in payload

    artifacts = payload.get("artifacts")
    assert isinstance(artifacts, dict)
    for name in artifacts.values():
        assert isinstance(name, str)
        assert name
        assert "/" not in name
        assert "\\" not in name
        assert ":" not in name


def test_get_run_unknown_id_returns_404(isolated_run_dirs: Path):
    resp = client.get("/runs/run-19990101-000000-000")
    assert resp.status_code == 404


def test_get_run_artifact_unknown_id_returns_404(isolated_run_dirs: Path):
    triage_resp = client.get("/runs/run-19990101-000000-000/triage")
    briefing_resp = client.get("/runs/run-19990101-000000-000/briefing")

    assert triage_resp.status_code == 404
    assert briefing_resp.status_code == 404


def test_get_run_artifact_rejects_path_traversal_like_id(isolated_run_dirs: Path):
    triage_resp = client.get("/runs/..%2F..%2Fwindows%2Fsystem32/triage")
    briefing_resp = client.get("/runs/..%2F..%2Fwindows%2Fsystem32/briefing")

    assert triage_resp.status_code == 404
    assert briefing_resp.status_code == 404
