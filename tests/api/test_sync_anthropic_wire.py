"""Sync drain Anthropic operator auth (F2) — hermetic via POST /sync."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import create_app
from opspilot.api.deps import reset_db_engine
from opspilot.llm.operator_auth import OperatorAnthropicAuth
from opspilot.persistence.models import OpsJobRow
from opspilot.persistence.repositories import oauth_credentials, work_items
from opspilot.persistence.repositories.ops_jobs import upsert_lease
from opspilot.services.operator_session import issue_session


@pytest.fixture
def sync_client(monkeypatch: pytest.MonkeyPatch, test_database_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-not-real")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    monkeypatch.setenv("OPSPILOT_CSRF_RELAX_DEV", "1")
    reset_db_engine()
    return TestClient(create_app(), raise_server_exceptions=False)


def _seed_oauth(db_session: Session) -> None:
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes="https://www.googleapis.com/auth/gmail.readonly",
        refresh_token_plaintext="rt",
    )
    db_session.commit()


def _noop_sync(session: Any, **kwargs: Any) -> dict[str, Any]:
    return {
        "account_email": "demo@example.com",
        "gmail_upserted": 0,
        "gmail_removed": 0,
        "calendar_upserted": 0,
        "gmail_total": 1,
        "meetings_total": 0,
        "gmail_truncated": False,
        "calendar_truncated": False,
    }


def _seed_one_untriaged(db_session: Session) -> None:
    t0 = datetime.now(UTC)
    work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_auth_1",
        source_type="gmail",
        subject_or_title="A",
        body_or_description="body",
        sender_or_requester="a@example.test",
        received_at=t0,
    )
    db_session.commit()


def test_sync_triage_flag_off_zero_anthropic_rows(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """ENABLED off + operator auth → drain triage builds no Anthropic; row delta 0."""
    import json

    from sqlalchemy import func, select

    from opspilot.llm.providers.fake import FakeProvider
    from opspilot.llm.routing import build_providers as real_bp
    from opspilot.llm.schemas.triage import TriagePayload
    from opspilot.llm.types import AttemptStatus, ProviderResult
    from opspilot.persistence.models import LlmCallRow
    from opspilot.services._llm import complete_structured_raising

    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "0")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "100")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")

    payload = {
        "urgency": "low",
        "urgency_reason": "routine",
        "category": "other",
        "category_reason": "general",
        "sentiment": "neutral",
        "sentiment_reason": "flat",
        "confidence": 0.5,
        "evidence_refs": [],
    }
    fake = FakeProvider(
        name="gemini",
        json_results=[ProviderResult(status=AttemptStatus.SUCCESS, text=json.dumps(payload), model="fake-v1")],
    )

    def _bp(**kwargs: Any) -> list[Any]:
        built = real_bp(order=["fake"], **kwargs)
        assert all(p.name != "anthropic" for p in built)
        return [fake]

    monkeypatch.setattr("opspilot.llm.routing.build_providers", _bp)
    before = int(
        db_session.scalar(select(func.count()).select_from(LlmCallRow).where(LlmCallRow.provider == "anthropic")) or 0
    )
    auth = OperatorAnthropicAuth(role="demo_operator")
    result = complete_structured_raising(
        task="triage",
        system="triage",
        user="item body",
        schema=TriagePayload,
        max_tokens=256,
        session=db_session,
        operator_auth=auth,
    )
    assert result is not None
    after = int(
        db_session.scalar(select(func.count()).select_from(LlmCallRow).where(LlmCallRow.provider == "anthropic")) or 0
    )
    assert after == before


def test_authorized_sync_passes_auth_to_drain(
    sync_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_oauth(db_session)
    _seed_one_untriaged(db_session)
    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _noop_sync)
    captured: list[object | None] = []

    def _fake_spawn(job_id: str, generation: int, ceiling: int, operator_auth: object | None = None) -> None:
        captured.append(operator_auth)

    monkeypatch.setattr("opspilot.api.v1.oauth_routes._spawn_sync_drain", _fake_spawn)
    token = issue_session(email="demo@example.com")
    sync_client.cookies.set("opspilot_operator", token)
    resp = sync_client.post("/api/v1/sync")
    assert resp.status_code == 202, resp.text
    assert len(captured) == 1
    assert isinstance(captured[0], OperatorAnthropicAuth)
    assert captured[0].role == "demo_operator"


def test_busy_lease_does_not_spawn_auth_unchanged(
    sync_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_oauth(db_session)
    _seed_one_untriaged(db_session)
    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _noop_sync)
    # Hold lease with a running job
    other = OpsJobRow(
        id="running-job",
        job_kind="sync_drain",
        day_utc=datetime.now(UTC).date(),
        status="running",
        force_override=False,
        request_ceiling=10,
        metadata_json={},
    )
    db_session.add(other)
    db_session.flush()
    upsert_lease(db_session, job_id="running-job", generation=1)
    db_session.commit()

    spawns: list[Any] = []

    def _fake_spawn(*args: Any, **kwargs: Any) -> None:
        spawns.append((args, kwargs))

    monkeypatch.setattr("opspilot.api.v1.oauth_routes._spawn_sync_drain", _fake_spawn)
    token = issue_session(email="demo@example.com")
    sync_client.cookies.set("opspilot_operator", token)
    resp = sync_client.post("/api/v1/sync")
    assert resp.status_code == 200, resp.text
    assert resp.json()["drain"] == "busy"
    assert spawns == []


def test_sequential_spawn_auth_then_none_sees_none(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, test_database_url: str
) -> None:
    """Real _spawn_sync_drain twice: from_session(verify_session) auth, then None."""
    import threading

    from opspilot.api.v1.oauth_routes import _spawn_sync_drain
    from opspilot.services.drain import DrainResult
    from opspilot.services.operator_session import verify_session

    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-not-real")

    token = issue_session(email="demo@example.com")
    auth = OperatorAnthropicAuth.from_session(verify_session(token))
    assert isinstance(auth, OperatorAnthropicAuth)
    assert auth.role == "demo_operator"

    captured: list[object | None] = []
    done = threading.Event()

    def _capture_drain(
        session: Any,
        *,
        job: Any,
        generation: int,
        ceiling: int | None = None,
        heartbeat_interval_s: int | None = None,
        operator_auth: object | None = None,
    ) -> DrainResult:
        captured.append(operator_auth)
        done.set()
        return DrainResult()

    monkeypatch.setattr("opspilot.services.drain.drain", _capture_drain)

    def _add_job(job_id: str) -> None:
        db_session.add(
            OpsJobRow(
                id=job_id,
                job_kind="sync_drain",
                day_utc=datetime.now(UTC).date(),
                status="running",
                force_override=False,
                request_ceiling=10,
                metadata_json={},
            )
        )
        db_session.commit()

    _add_job("spawn-auth")
    done.clear()
    captured.clear()
    _spawn_sync_drain("spawn-auth", 1, 10, auth)
    assert done.wait(timeout=10), "drain thread did not run for auth spawn"
    assert len(captured) == 1
    assert isinstance(captured[0], OperatorAnthropicAuth)
    assert captured[0].role == "demo_operator"

    _add_job("spawn-none")
    done.clear()
    captured.clear()
    _spawn_sync_drain("spawn-none", 1, 10, None)
    assert done.wait(timeout=10), "drain thread did not run for None spawn"
    assert len(captured) == 1
    assert captured[0] is None


def test_pin_no_operator_auth_contextvar_in_src() -> None:
    root = Path("src")
    hits: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "ContextVar" in text and ("operator_auth" in text or "sync_drain_operator" in text):
            hits.append(path.as_posix())
        if "_sync_drain_operator_auth" in text:
            hits.append(path.as_posix())
    assert hits == [], hits
