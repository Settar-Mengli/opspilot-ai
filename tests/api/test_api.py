import os
import subprocess
import sys
from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from opspilot.api.main import app

client = TestClient(app)

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
