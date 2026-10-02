#!/usr/bin/env python3
"""B5 live smoke — operator-gated; never executed by CI or this fix-pass Build.

Phases start/stop their own uvicorn with process-only env (never writes .env).
Prints counts and Y/N only — never tokens, cookies, allowlist values, or bodies.
At most one real Gmail send for the entire run.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
API_HOST = "127.0.0.1"
API_PORT = 8010  # avoid colliding with a long-lived local :8000
BASE = f"http://{API_HOST}:{API_PORT}"


def _die(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(code)


def _yn(ok: bool) -> str:
    return "Y" if ok else "N"


def _load_operator_email() -> str:
    from opspilot.persistence.db import create_engine, create_session_factory, database_host_label, get_database_url
    from opspilot.persistence.repositories import oauth_credentials

    print(f"database_host={database_host_label()}")
    engine = create_engine(get_database_url())
    sf = create_session_factory(engine)
    with sf() as session:
        cred = oauth_credentials.get_decrypted_refresh(session, provider="google")
    if cred is None:
        _die("no_operator_google_credential")
    email, _refresh = cred
    return email.strip().lower()


def _issue_cookie(email: str) -> str:
    from opspilot.services.operator_session import COOKIE_NAME, issue_session

    token = issue_session(email=email)
    # Never print token — only confirm mint.
    print(f"operator_session_minted={_yn(bool(token))} cookie_name={COOKIE_NAME}")
    return token


def _phase_env(*, demo: str, allowlist: str) -> dict[str, str]:
    env = os.environ.copy()
    # Process-only overrides — never write .env.
    env["OPSPILOT_DEMO_MODE"] = demo
    env["OPSPILOT_SEND_RECIPIENT_ALLOWLIST"] = allowlist
    for k in ("OPSPILOT_FORCE_RULES", "OPSPILOT_LLM_DISABLE", "OPSPILOT_CSRF_RELAX_DEV", "FORCE_RULES", "LLM_DISABLE"):
        env.pop(k, None)
        env.pop(f"OPSPILOT_{k}" if not k.startswith("OPSPILOT_") else k, None)
    env.pop("OPSPILOT_FORCE_RULES", None)
    env.pop("OPSPILOT_LLM_DISABLE", None)
    env.pop("OPSPILOT_CSRF_RELAX_DEV", None)
    return env


def _start_api(env: dict[str, str]) -> subprocess.Popen[str]:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "opspilot.api.app:app",
        "--host",
        API_HOST,
        "--port",
        str(API_PORT),
        "--log-level",
        "warning",
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            _die("api_exited_early")
        try:
            r = httpx.get(f"{BASE}/api/v1/health", timeout=1.0)
            if r.status_code == 200:
                print("health=Y")
                return proc
        except Exception:
            time.sleep(0.25)
    _stop(proc)
    _die("api_health_timeout")
    raise AssertionError("unreachable")


def _stop(proc: subprocess.Popen[str] | None) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        if sys.platform == "win32":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def _client(cookie: str) -> httpx.Client:
    from opspilot.services.operator_session import COOKIE_NAME

    return httpx.Client(
        base_url=BASE,
        cookies={COOKIE_NAME: cookie},
        headers={"Origin": "http://127.0.0.1:5173"},
        timeout=120.0,
    )


def _count_sql() -> dict[str, int]:
    from sqlalchemy import text

    from opspilot.persistence.db import create_engine, create_session_factory, get_database_url

    engine = create_engine(get_database_url())
    sf = create_session_factory(engine)
    out: dict[str, int] = {}
    with sf() as session:
        for table in ("work_items", "mail_drafts", "mail_send_audit", "llm_calls"):
            out[table] = int(session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
    return out


def _print_counts(label: str, counts: dict[str, int]) -> None:
    parts = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    print(f"counts_{label} {parts}")


def _ask_draft(client: httpx.Client) -> dict[str, Any]:
    with client.stream(
        "POST",
        "/api/v1/ask/stream",
        json={"question": "Draft a short reply to the latest inbox mail asking to confirm Friday."},
    ) as resp:
        if resp.status_code != 200:
            _die(f"ask_stream_status={resp.status_code}")
        draft: dict[str, Any] | None = None
        for line in resp.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = json.loads(line[5:].strip() or "{}")
            if payload.get("type") == "draft":
                draft = payload.get("data") or payload
            if payload.get("type") in {"final", "error"}:
                break
    if not draft or not draft.get("draft_id"):
        _die("ask_no_draft")
    print("ask_draft=Y")
    return draft


def _approve(client: httpx.Client, draft_id: str, payload_sha: str, key: str) -> httpx.Response:
    return client.post(
        f"/api/v1/mail/drafts/{draft_id}/approve",
        json={"payload_sha256": payload_sha, "idempotency_key": key},
    )


def _get_draft_sha(client: httpx.Client, draft_id: str) -> str:
    # Approve body needs sha; draft event may omit it — fetch via edit no-op is heavy; use SQL.
    from sqlalchemy import text

    from opspilot.persistence.db import create_engine, create_session_factory, get_database_url

    engine = create_engine(get_database_url())
    sf = create_session_factory(engine)
    with sf() as session:
        row = session.execute(
            text("SELECT payload_sha256 FROM mail_drafts WHERE id = :id"),
            {"id": draft_id},
        ).one_or_none()
    if row is None:
        _die("draft_missing")
    return str(row[0])


def main() -> None:
    print("live_smoke_b5 start (not for CI)")
    operator = _load_operator_email()
    allow_raw = os.environ.get("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "").strip()
    allow_parts = [p.strip().lower() for p in allow_raw.split(",") if p.strip()]
    allow_ok = len(allow_parts) == 1 and allow_parts[0] == operator
    print(f"allowlist_exact_one={_yn(len(allow_parts) == 1)}")
    print(f"allowlist_matches_operator={_yn(allow_ok)}")
    if not allow_ok:
        _die("allowlist_must_be_exactly_operator_email")

    cookie = _issue_cookie(operator)
    before = _count_sql()
    _print_counts("before", before)

    sends = 0
    proc: subprocess.Popen[str] | None = None
    try:
        # --- Phase send: DEMO=0 + allowlist ---
        print("phase=send")
        proc = _start_api(_phase_env(demo="0", allowlist=operator))
        with _client(cookie) as client:
            sync = client.post("/api/v1/oauth/google/sync")
            print(f"sync_status={sync.status_code}")
            if sync.status_code != 200:
                _die("sync_failed")
            scopes = client.get("/api/v1/oauth/google/status")
            print(f"scopes_status={scopes.status_code}")
            draft = _ask_draft(client)
            draft_id = str(draft["draft_id"])
            sha = _get_draft_sha(client, draft_id)
            key_a = str(uuid.uuid4())
            resp = _approve(client, draft_id, sha, key_a)
            print(f"approve_send_status={resp.status_code}")
            if resp.status_code != 200:
                _die("approve_send_failed")
            sends += 1
            print(f"real_sends={sends}")
            resp_409 = _approve(client, draft_id, sha, str(uuid.uuid4()))
            print(f"reapprove_status={resp_409.status_code} expect_409={_yn(resp_409.status_code == 409)}")
            if resp_409.status_code != 409:
                _die("expected_409_on_second_claim")
            resp_replay = _approve(client, draft_id, sha, key_a)
            body = resp_replay.json()
            replay_ok = resp_replay.status_code == 200 and body.get("status") == "idempotent_replay"
            print(f"idempotent_replay={_yn(replay_ok)}")
            if not replay_ok:
                _die("idempotent_replay_failed")
        _stop(proc)
        proc = None

        # --- Phase demo: DEMO=1 ---
        print("phase=demo")
        proc = _start_api(_phase_env(demo="1", allowlist=operator))
        with _client(cookie) as client:
            draft = _ask_draft(client)
            draft_id = str(draft["draft_id"])
            sha = _get_draft_sha(client, draft_id)
            resp = _approve(client, draft_id, sha, str(uuid.uuid4()))
            print(f"demo_approve_status={resp.status_code} expect_403={_yn(resp.status_code == 403)}")
            if resp.status_code != 403:
                _die("demo_expected_403")
        _stop(proc)
        proc = None

        # --- Phase allowlist empty ---
        print("phase=allowlist_empty")
        proc = _start_api(_phase_env(demo="0", allowlist=""))
        with _client(cookie) as client:
            draft = _ask_draft(client)
            draft_id = str(draft["draft_id"])
            sha = _get_draft_sha(client, draft_id)
            resp = _approve(client, draft_id, sha, str(uuid.uuid4()))
            print(f"empty_allowlist_status={resp.status_code} expect_403={_yn(resp.status_code == 403)}")
            if resp.status_code != 403:
                _die("empty_allowlist_expected_403")
        _stop(proc)
        proc = None

        after = _count_sql()
        _print_counts("after", after)
        print(f"delta_mail_send_audit={after['mail_send_audit'] - before['mail_send_audit']}")
        print(f"real_sends_total={sends}")
        if sends != 1:
            _die("expected_exactly_one_real_send")
        print("live_smoke_b5=PASS")
    finally:
        _stop(proc)


if __name__ == "__main__":
    main()
