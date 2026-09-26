"""API tests — legacy aliases + Postgres-backed handlers."""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from opspilot.api.app import app
from opspilot.api.deps import reset_db_engine
from opspilot.jobs.import_json import upsert_run_from_metadata, upsert_work_items
from opspilot.models.schemas import PipelineExecutionError
from opspilot.persistence.models import TriageDecisionRow

client = TestClient(app)


class _FakeExecutor:
    def __init__(self, submit_impl):
        self._submit_impl = submit_impl

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def submit(self, fn, *args, **kwargs):
        return self

    def result(self, timeout=None):
        return self._submit_impl()


@pytest.fixture(autouse=True)
def _api_uses_test_db(test_database_url: str, db_session: Session):
    """Point API deps at truncate-managed test DB for every API test."""
    os.environ["DATABASE_URL"] = test_database_url
    reset_db_engine()
    yield
    reset_db_engine()


@pytest.fixture
def isolated_run_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    output_dir = tmp_path / "output"
    history_dir = tmp_path / "history" / "runs"
    output_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("opspilot.api.paths.API_OUTPUT_DIR", output_dir)
    monkeypatch.setattr("opspilot.api.paths.HISTORY_RUNS_DIR", history_dir)
    monkeypatch.setattr("opspilot.api.services.pipeline.API_OUTPUT_DIR", output_dir)
    monkeypatch.setattr("opspilot.api.v1.routes.API_OUTPUT_DIR", output_dir)
    return tmp_path


def _seed_run(session: Session, tmp_path: Path, run_id: str, metadata: dict) -> None:
    run_dir = tmp_path / "history" / "runs" / "2026" / "05" / "30" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifacts = metadata.get("artifacts") or {}
    for _logical, filename in artifacts.items():
        if not isinstance(filename, str):
            continue
        path = run_dir / filename
        if not path.exists():
            if filename.endswith(".json"):
                path.write_text("[]", encoding="utf-8")
            else:
                path.write_text("OpsPilot AI Daily Executive Briefing\n", encoding="utf-8")
    (run_dir / "run.json").write_text(json.dumps(metadata), encoding="utf-8")
    upsert_run_from_metadata(session, metadata, run_dir)
    session.commit()


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.text == "ok"


def test_run_pipeline_success():
    resp = client.post("/api/v1/runs", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "run_id" in body


def test_run_requires_date():
    resp = client.post("/api/v1/runs", json={"input_file": "sample_input.json"})
    assert resp.status_code == 422
    payload = resp.json()
    assert "error" in payload
    assert payload["error"]["code"] == "validation_error"


def test_run_rejects_invalid_date_format():
    resp = client.post("/api/v1/runs", json={"input_file": "sample_input.json", "date": "29-05-2026"})
    assert resp.status_code == 422


def test_run_rejects_path_traversal():
    resp = client.post("/api/v1/runs", json={"input_file": "../sample_input.json", "date": "2026-05-29"})
    assert resp.status_code == 400


def test_run_timeout_returns_safe_error(monkeypatch: pytest.MonkeyPatch):
    def _timeout():
        raise FuturesTimeoutError()

    monkeypatch.setattr(
        "opspilot.api.services.pipeline.ThreadPoolExecutor",
        lambda *a, **k: _FakeExecutor(_timeout),
    )
    resp = client.post("/api/v1/runs", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    assert resp.status_code == 504
    payload = resp.json()
    assert payload["error"]["code"] == "pipeline_timeout"


def test_run_subprocess_failure_returns_safe_error(monkeypatch: pytest.MonkeyPatch):
    def _failed():
        raise PipelineExecutionError("traceback: private detail")

    monkeypatch.setattr(
        "opspilot.api.services.pipeline.ThreadPoolExecutor",
        lambda *a, **k: _FakeExecutor(_failed),
    )
    resp = client.post("/api/v1/runs", json={"input_file": "sample_input.json", "date": "2026-05-29"})
    assert resp.status_code == 500
    payload = resp.json()
    assert payload["error"]["code"] == "pipeline_failed"
    assert "private detail" not in str(payload)


def test_get_briefing(db_session: Session, tmp_path: Path):
    upsert_work_items(
        db_session,
        [
            {
                "id": "WI-001",
                "source_type": "email",
                "subject_or_title": "Fixture",
                "body_or_description": "Body",
                "sender_or_requester": "a@b.c",
                "received_at": "2026-05-29T00:00:00Z",
                "tags": [],
            }
        ],
    )
    db_session.commit()
    _seed_run(
        db_session,
        tmp_path,
        "run-20260529-000000-001",
        {
            "run_id": "run-20260529-000000-001",
            "started_at": "2026-05-29T00:00:00Z",
            "finished_at": "2026-05-29T00:00:01Z",
            "status": "success",
            "artifacts": {"daily_briefing": "daily_briefing.txt"},
        },
    )
    run_dir = tmp_path / "history" / "runs" / "2026" / "05" / "30" / "run-20260529-000000-001"
    (run_dir / "daily_briefing.txt").write_text("OpsPilot AI Daily Executive Briefing - fixture\n", encoding="utf-8")
    upsert_run_from_metadata(
        db_session,
        json.loads((run_dir / "run.json").read_text(encoding="utf-8")),
        run_dir,
    )
    db_session.commit()

    resp = client.get("/api/v1/briefing")
    assert resp.status_code == 200
    assert "OpsPilot AI Daily Executive Briefing" in resp.text


def test_get_triage(db_session: Session):
    upsert_work_items(
        db_session,
        [
            {
                "id": "WI-001",
                "source_type": "email",
                "subject_or_title": "Checkout errors",
                "body_or_description": "Body",
                "sender_or_requester": "a@b.c",
                "received_at": "2026-05-29T00:00:00Z",
                "tags": [],
            }
        ],
    )
    db_session.add(
        TriageDecisionRow(
            work_item_id="WI-001",
            run_id=None,
            urgency="high",
            urgency_reason="fixture",
            category="incident",
            category_reason="fixture",
            sentiment="negative",
            sentiment_reason="fixture",
        )
    )
    db_session.commit()

    resp = client.get("/api/v1/triage")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)
    assert payload
    assert payload[0]["subject_or_title"] == "Checkout errors"
    assert "urgency_reason" in payload[0]
    categories = {record["category"] for record in payload}
    assert categories.issubset({"incident", "request", "admin", "follow_up", "other"})


def test_get_runs_returns_empty_list_when_history_missing():
    resp = client.get("/api/v1/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_runs_returns_metadata_after_pipeline_run(db_session: Session, tmp_path: Path):
    upsert_work_items(
        db_session,
        [
            {
                "id": "WI-001",
                "source_type": "email",
                "subject_or_title": "A",
                "body_or_description": "B",
                "sender_or_requester": "a@b.c",
                "received_at": "2026-05-29T00:00:00Z",
                "tags": [],
            }
        ],
    )
    db_session.commit()
    run_id = "run-20260530-120000-001"
    _seed_run(
        db_session,
        tmp_path,
        run_id,
        {
            "run_id": run_id,
            "started_at": "2026-05-30T12:00:00Z",
            "finished_at": "2026-05-30T12:00:01Z",
            "duration_ms": 1000,
            "status": "success",
            "item_count": 1,
            "triage_count": 1,
            "artifacts": {
                "triage_results": "triage_results.json",
                "daily_briefing": "daily_briefing.txt",
            },
        },
    )
    resp = client.get("/api/v1/runs")
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 1
    assert payload[0]["run_id"] == run_id


def test_get_runs_metadata_is_sanitized_and_safe(db_session: Session, tmp_path: Path):
    run_id = "run-20260530-120000-002"
    _seed_run(
        db_session,
        tmp_path,
        run_id,
        {
            "run_id": run_id,
            "started_at": "2026-05-30T12:00:00Z",
            "finished_at": "2026-05-30T12:00:01Z",
            "status": "success",
            "input_file": "C:/secret/path.json",
            "output_dir": "C:/secret/out",
            "history_dir": "C:/secret/history",
            "artifacts": {"triage_results": "triage_results.json"},
        },
    )
    resp = client.get("/api/v1/runs")
    assert resp.status_code == 200
    item = resp.json()[0]
    assert "input_file" not in item
    assert "output_dir" not in item
    assert "history_dir" not in item
    assert item["run_id"] == run_id


def test_get_runs_metadata_allowlist_and_artifact_filtering(db_session: Session, tmp_path: Path):
    run_id = "run-20260530-120000-003"
    _seed_run(
        db_session,
        tmp_path,
        run_id,
        {
            "run_id": run_id,
            "started_at": "2026-05-30T12:00:00Z",
            "finished_at": "2026-05-30T12:00:01Z",
            "status": "success",
            "artifacts": {
                "triage_results": "triage_results.json",
                "daily_briefing": "daily briefing.txt",
                "secret_notes": "notes.txt",
            },
        },
    )
    resp = client.get("/api/v1/runs")
    artifacts = resp.json()[0]["artifacts"]
    assert "triage_results" in artifacts
    assert "daily_briefing" not in artifacts  # space rejected
    assert "secret_notes" not in artifacts


def test_get_runs_sorted_newest_first(db_session: Session, tmp_path: Path):
    _seed_run(
        db_session,
        tmp_path,
        "run-20260530-100000-001",
        {
            "run_id": "run-20260530-100000-001",
            "started_at": "2026-05-30T10:00:00Z",
            "finished_at": "2026-05-30T10:00:01Z",
            "status": "success",
            "artifacts": {},
        },
    )
    _seed_run(
        db_session,
        tmp_path,
        "run-20260530-110000-001",
        {
            "run_id": "run-20260530-110000-001",
            "started_at": "2026-05-30T11:00:00Z",
            "finished_at": "2026-05-30T11:00:01Z",
            "status": "success",
            "artifacts": {},
        },
    )
    resp = client.get("/api/v1/runs")
    ids = [item["run_id"] for item in resp.json()]
    assert ids[0] == "run-20260530-110000-001"


def test_get_run_triage_returns_artifact_for_run(db_session: Session, tmp_path: Path):
    run_id = "run-20260530-120000-010"
    run_dir = tmp_path / "history" / "runs" / "2026" / "05" / "30" / run_id
    run_dir.mkdir(parents=True)
    triage = [
        {
            "id": "WI-001",
            "urgency": "low",
            "urgency_reason": "x",
            "category": "other",
            "category_reason": "x",
            "sentiment": "neutral",
            "sentiment_reason": "x",
        }
    ]
    (run_dir / "triage_results.json").write_text(json.dumps(triage), encoding="utf-8")
    metadata = {
        "run_id": run_id,
        "started_at": "2026-05-30T12:00:00Z",
        "finished_at": "2026-05-30T12:00:01Z",
        "status": "success",
        "artifacts": {"triage_results": "triage_results.json"},
    }
    (run_dir / "run.json").write_text(json.dumps(metadata), encoding="utf-8")
    upsert_run_from_metadata(db_session, metadata, run_dir)
    db_session.commit()

    resp = client.get(f"/api/v1/runs/{run_id}/triage")
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == "WI-001"


def test_get_run_briefing_returns_artifact_for_run(db_session: Session, tmp_path: Path):
    run_id = "run-20260530-120000-011"
    run_dir = tmp_path / "history" / "runs" / "2026" / "05" / "30" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "daily_briefing.txt").write_text("OpsPilot AI Daily Executive Briefing\n", encoding="utf-8")
    metadata = {
        "run_id": run_id,
        "started_at": "2026-05-30T12:00:00Z",
        "finished_at": "2026-05-30T12:00:01Z",
        "status": "success",
        "artifacts": {"daily_briefing": "daily_briefing.txt"},
    }
    (run_dir / "run.json").write_text(json.dumps(metadata), encoding="utf-8")
    upsert_run_from_metadata(db_session, metadata, run_dir)
    db_session.commit()

    resp = client.get(f"/api/v1/runs/{run_id}/briefing")
    assert resp.status_code == 200
    assert "OpsPilot AI Daily Executive Briefing" in resp.text


def test_get_run_metadata_for_specific_run(db_session: Session, tmp_path: Path):
    run_id = "run-20260530-120000-012"
    _seed_run(
        db_session,
        tmp_path,
        run_id,
        {
            "run_id": run_id,
            "started_at": "2026-05-30T12:00:00Z",
            "finished_at": "2026-05-30T12:00:01Z",
            "status": "success",
            "item_count": 3,
            "artifacts": {},
        },
    )
    resp = client.get(f"/api/v1/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == run_id
    assert resp.json()["item_count"] == 3


def test_get_run_metadata_is_sanitized_and_safe(db_session: Session, tmp_path: Path):
    run_id = "run-20260530-120000-013"
    _seed_run(
        db_session,
        tmp_path,
        run_id,
        {
            "run_id": run_id,
            "started_at": "2026-05-30T12:00:00Z",
            "finished_at": "2026-05-30T12:00:01Z",
            "status": "success",
            "input_file": "C:/secret.json",
            "artifacts": {},
        },
    )
    resp = client.get(f"/api/v1/runs/{run_id}")
    assert "input_file" not in resp.json()


def test_get_run_metadata_allowlist_and_artifact_filtering(db_session: Session, tmp_path: Path):
    run_id = "run-20260530-120000-014"
    _seed_run(
        db_session,
        tmp_path,
        run_id,
        {
            "run_id": run_id,
            "started_at": "2026-05-30T12:00:00Z",
            "finished_at": "2026-05-30T12:00:01Z",
            "status": "success",
            "artifacts": {
                "triage_results": "triage_results.json",
                "daily_briefing": "@briefing.txt",
            },
        },
    )
    artifacts = client.get(f"/api/v1/runs/{run_id}").json()["artifacts"]
    assert "triage_results" in artifacts
    assert "daily_briefing" not in artifacts


def test_get_run_unknown_id_returns_404():
    resp = client.get("/api/v1/runs/run-19990101-000000-000")
    assert resp.status_code == 404


def test_get_run_metadata_rejects_path_traversal_like_id():
    resp = client.get("/api/v1/runs/..%2F..%2Fwindows%2Fsystem32")
    assert resp.status_code == 404


def test_get_run_artifact_unknown_id_returns_404():
    assert client.get("/api/v1/runs/run-19990101-000000-000/triage").status_code == 404
    assert client.get("/api/v1/runs/run-19990101-000000-000/briefing").status_code == 404


def test_get_run_artifact_rejects_path_traversal_like_id():
    assert client.get("/api/v1/runs/..%2F..%2Fwindows%2Fsystem32/triage").status_code == 404
    assert client.get("/api/v1/runs/..%2F..%2Fwindows%2Fsystem32/briefing").status_code == 404


def test_settings_get_ok_patch_removed():
    resp = client.get("/api/v1/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert "provider" in body
    assert "api_key" not in body
    patch = client.patch("/api/v1/settings", json={"provider": "anthropic"})
    assert patch.status_code in {404, 405, 422}


def test_cors_preflight_allows_post_for_local_origin():
    resp = client.options(
        "/api/v1/runs",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code in {200, 204}
    assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_cors_preflight_disallows_non_local_origin():
    resp = client.options(
        "/api/v1/runs",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "https://evil.example"
