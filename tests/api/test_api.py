import os
import sys
import pytest
from fastapi.testclient import TestClient

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

def test_get_briefing():
    resp = client.get("/briefing")
    assert resp.status_code == 200
    assert "OpsPilot AI Daily Executive Briefing" in resp.text

def test_get_triage():
    resp = client.get("/triage")
    assert resp.status_code == 200
    assert 'urgency_reason' in resp.text
