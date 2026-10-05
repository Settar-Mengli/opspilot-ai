"""Settings job summary includes rules_fallback_count and reauth_needed (B6 F6)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.persistence.models import OpsJobRow


@pytest.fixture()
def client(test_database_url: str) -> TestClient:
    from opspilot.api.app import create_app

    return TestClient(create_app())


def test_settings_job_summary_includes_rules_fallback_and_reauth(
    client: TestClient,
    db_session: Session,
) -> None:
    finished = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    morning = OpsJobRow(
        id="job-morning-summary-1",
        job_kind="morning",
        day_utc=date(2026, 10, 1),
        status="succeeded",
        force_override=False,
        finished_at=finished,
        triaged=5,
        pending=0,
        rules_fallback_count=2,
        reauth_needed=True,
        request_count=10,
        request_ceiling=60,
    )
    db_session.add(morning)
    db_session.commit()

    resp = client.get("/api/v1/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert "last_morning" in body
    job = body["last_morning"]
    assert job is not None
    assert job["rules_fallback_count"] == 2
    assert job["reauth_needed"] is True
    assert job["triaged"] == 5
    assert job["pending"] == 0
