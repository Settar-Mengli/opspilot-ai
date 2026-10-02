"""ASGI-level Ask stream disconnect cancels further provider work."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.requests import Request

from opspilot.api.app import app
from opspilot.api.deps import get_db_session, reset_db_engine
from opspilot.api.v1 import routes_ask
from opspilot.llm.providers.fake import FakeProvider
from opspilot.llm.types import AttemptStatus, ProviderResult
from opspilot.persistence.repositories import work_items


@pytest.fixture()
def api_client(test_database_url: str, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "100")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")
    monkeypatch.setenv("OPSPILOT_CSRF_RELAX_DEV", "1")
    reset_db_engine()

    def _override() -> Iterator[Session]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db_session] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    reset_db_engine()


def test_ask_stream_client_disconnect_stops_before_draft(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Client disconnect mid-stream: no further provider calls, no draft.

    TestClient may read past yields in one chunk, so cancel_check waits at the
    start of step 2 until the client has flipped Request.is_disconnected via the
    ASGI poller path (anyio.from_thread.run → is_disconnected).
    """
    wi_id = work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_disc_asgi",
        source_type="gmail",
        subject_or_title="Hello",
        body_or_description="Body",
        sender_or_requester="demo@example.com",
        received_at=datetime(2026, 10, 1, tzinfo=UTC),
        thread_id="thr_disc_asgi",
    )
    db_session.execute(text("DELETE FROM mail_drafts WHERE gmail_provider_id = 'msg_disc_asgi'"))
    db_session.commit()

    disconnect = {"v": False}
    client_saw_tool_end = threading.Event()

    async def _is_disconnected(self: Request) -> bool:  # noqa: ARG001
        return bool(disconnect["v"])

    monkeypatch.setattr(Request, "is_disconnected", _is_disconnected)

    calls = {"n": 0}

    class GatedFake(FakeProvider):
        def complete_json(self, **kwargs):  # type: ignore[no-untyped-def]
            calls["n"] += 1
            if calls["n"] == 1:
                return ProviderResult(
                    status=AttemptStatus.SUCCESS,
                    text=json.dumps({"kind": "tool", "tool": "search_items", "args": {"query": "x", "limit": 5}}),
                    model="fake-v1",
                    input_tokens=1,
                    output_tokens=1,
                    latency_ms=1,
                )
            return ProviderResult(
                status=AttemptStatus.SUCCESS,
                text=json.dumps(
                    {
                        "kind": "tool",
                        "tool": "draft_reply",
                        "args": {"work_item_id": wi_id, "subject": "Re: Hello", "body": "Thanks"},
                    }
                ),
                model="fake-v1",
                input_tokens=1,
                output_tokens=1,
                latency_ms=1,
            )

    monkeypatch.setattr("opspilot.agent.loop.build_providers", lambda: [GatedFake(name="gemini")])

    real_poller = routes_ask._disconnect_poller

    def _wrap_poller(http_request: Request):
        cancel_check, stop = real_poller(http_request)
        checks = {"n": 0}

        def traced() -> bool:
            checks["n"] += 1
            # Step1: before(1) + after(2); step2 before(3) — wait for client disconnect.
            if checks["n"] == 3:
                assert client_saw_tool_end.wait(timeout=5.0)
                deadline = time.time() + 5.0
                while time.time() < deadline and not disconnect["v"]:
                    time.sleep(0.02)
                assert disconnect["v"] is True
                return cancel_check()
            return cancel_check()

        return traced, stop

    monkeypatch.setattr(routes_ask, "_disconnect_poller", _wrap_poller)

    with api_client.stream(
        "POST",
        "/api/v1/ask/stream",
        json={"question": "Hi", "assistant_name": "OpsPilot"},
        headers={"Origin": "http://127.0.0.1:5173"},
    ) as resp:
        assert resp.status_code == 200
        buf = ""
        for chunk in resp.iter_text():
            buf += chunk
            if "tool_end" in buf:
                client_saw_tool_end.set()
                disconnect["v"] = True
                break

    time.sleep(0.2)
    assert disconnect["v"] is True
    n = db_session.execute(text("SELECT COUNT(*) FROM mail_drafts WHERE gmail_provider_id = 'msg_disc_asgi'")).scalar()
    assert int(n or 0) == 0
    assert calls["n"] == 1
