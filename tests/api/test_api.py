import os
import json
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


def _write_run_metadata(history_dir: Path, run_id: str, payload: dict) -> None:
    run_dir = history_dir / "2026" / "05" / "30" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps(payload), encoding="utf-8")

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

def test_get_briefing(isolated_run_dirs: Path):
    output_dir = isolated_run_dirs / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "daily_briefing.txt").write_text(
        "OpsPilot AI Daily Executive Briefing - 2026-05-29\n\nTotal Work Items: 1\n",
        encoding="utf-8",
    )
    resp = client.get("/briefing")
    assert resp.status_code == 200
    assert "OpsPilot AI Daily Executive Briefing" in resp.text


def test_get_triage(isolated_run_dirs: Path):
    output_dir = isolated_run_dirs / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "triage_results.json").write_text(
        json.dumps(
            [
                {
                    "id": "WI-001",
                    "urgency": "high",
                    "urgency_reason": "fixture",
                    "category": "incident",
                    "category_reason": "fixture",
                    "sentiment": "negative",
                    "sentiment_reason": "fixture",
                }
            ]
        ),
        encoding="utf-8",
    )
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
        assert "input_file" not in item
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


def test_get_runs_metadata_allowlist_and_artifact_filtering(isolated_run_dirs: Path):
    history_dir = isolated_run_dirs / "history" / "runs"
    run_id = "run-20260530-120000-123"
    _write_run_metadata(
        history_dir,
        run_id,
        {
            "run_id": run_id,
            "started_at": "2026-05-30T12:00:00Z",
            "finished_at": "2026-05-30T12:01:00Z",
            "duration_ms": 1000,
            "status": "success",
            "item_count": 6,
            "triage_count": 6,
            "action_count": 4,
            "suggested_response_count": 6,
            "error": None,
            "input_file": "data/raw/sample_input.json",
            "output_dir": "C:/sensitive/output",
            "history_dir": "C:/sensitive/history",
            "unexpected_key": "must_not_be_exposed",
            "artifacts": {
                "triage_results": "triage_results.json",
                "action_items": "../action_items.json",
                "suggested_responses": "",
                "daily_briefing": "daily briefing.txt",
                "custom": "custom.json",
            },
        },
    )

    resp = client.get("/runs")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)
    assert len(payload) == 1

    item = payload[0]
    assert item["run_id"] == run_id
    assert "input_file" not in item
    assert "output_dir" not in item
    assert "history_dir" not in item
    assert "unexpected_key" not in item

    expected_keys = {
        "run_id",
        "started_at",
        "finished_at",
        "duration_ms",
        "status",
        "item_count",
        "triage_count",
        "action_count",
        "suggested_response_count",
        "error",
        "artifacts",
    }
    assert set(item.keys()).issubset(expected_keys)

    artifacts = item.get("artifacts")
    assert artifacts == {"triage_results": "triage_results.json"}


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

    assert "input_file" not in payload
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


def test_get_run_metadata_allowlist_and_artifact_filtering(isolated_run_dirs: Path):
    history_dir = isolated_run_dirs / "history" / "runs"
    run_id = "run-20260530-121500-456"
    _write_run_metadata(
        history_dir,
        run_id,
        {
            "run_id": run_id,
            "status": "success",
            "item_count": 1,
            "output_dir": "C:/sensitive/output",
            "unexpected": "leak",
            "artifacts": {
                "triage_results": "triage_results.json",
                "action_items": "nested/action_items.json",
                "suggested_responses": "..\\suggested_responses.json",
                "daily_briefing": "@briefing.txt",
            },
        },
    )

    run_meta_resp = client.get(f"/runs/{run_id}")
    assert run_meta_resp.status_code == 200

    payload = run_meta_resp.json()
    assert payload["run_id"] == run_id
    assert payload["status"] == "success"
    assert payload["item_count"] == 1
    assert "output_dir" not in payload
    assert "unexpected" not in payload
    assert payload.get("artifacts") == {"triage_results": "triage_results.json"}


def test_get_run_unknown_id_returns_404(isolated_run_dirs: Path):
    resp = client.get("/runs/run-19990101-000000-000")
    assert resp.status_code == 404


def test_get_run_metadata_rejects_path_traversal_like_id(isolated_run_dirs: Path):
    resp = client.get("/runs/..%2F..%2Fwindows%2Fsystem32")
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


def test_cors_preflight_allows_post_for_local_origin():
    resp = client.options(
        "/run",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    allow_methods = resp.headers.get("access-control-allow-methods", "")
    assert "POST" in allow_methods
    assert "GET" in allow_methods


def test_cors_preflight_disallows_non_local_origin():
    resp = client.options(
        "/run",
        headers={
            "Origin": "http://evil.local:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert resp.status_code == 400

    allow_origin = resp.headers.get("access-control-allow-origin")
    assert allow_origin is None or allow_origin != "*"
