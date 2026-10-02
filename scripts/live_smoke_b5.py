#!/usr/bin/env python3
"""B5 live smoke — operator-gated; never executed by CI or hermetic Build.

Default mode: NO real Gmail send. Real send requires ``--send`` (still capped at one).
Phases start/stop their own uvicorn with process-only env (never writes .env).
Prints counts and Y/N only — never tokens, cookies, allowlist values, addresses, or bodies.

Ask targets a read-only-selected self-sent gmail work item; draft recipients are verified
before any approve call so allowlist/DEMO gates are proven on an operator-addressed draft.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

import httpx

ROOT = Path(__file__).resolve().parents[1]
API_HOST = "127.0.0.1"
API_PORT = 8010  # avoid colliding with a long-lived local :8000
BASE = f"http://{API_HOST}:{API_PORT}"
SMOKE_MAX_ASKS = 3
SYNC_PATH = "/api/v1/sync"
# Gitignored (see repo .gitignore ``tmp/``). May contain addresses / subjects / tokens.
API_LOG_DIR = ROOT / "tmp" / "live_smoke"

# Fail codes for draft gate (tests assert exact strings after ``FAIL: ``).
FAIL_NO_SELF_SENT = "no_self_sent_item"
FAIL_DRAFT_WRONG_ITEM = "draft_wrong_item"
FAIL_DRAFT_RECIPIENT_COUNT = "draft_recipient_count"
FAIL_DRAFT_RECIPIENT_NOT_OPERATOR = "draft_recipient_not_operator"

_SQL_WRITE_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|MERGE|UPSERT|REPLACE)\b",
    re.IGNORECASE,
)


def _die(msg: str, code: int = 1) -> NoReturn:
    print(f"FAIL: {msg}")
    raise SystemExit(code)


def _yn(ok: bool) -> str:
    return "Y" if ok else "N"


def _host_label() -> str:
    from opspilot.persistence.db import database_host_label

    return database_host_label()


def ask_prompt_for_work_item(work_item_id: str) -> str:
    """Pinned Ask question that names the exact work_item_id (never includes addresses)."""
    return (
        f"Draft a short reply to work item {work_item_id} asking to confirm Friday. "
        f"You must call draft_reply with work_item_id exactly equal to {work_item_id}."
    )


def _normalize_addr(raw: str) -> str:
    """Product normalisation — import only; never re-implement."""
    from opspilot.services.mail_address import parse_single_addr_spec

    return parse_single_addr_spec(raw)


def _preflight(*, operator: str) -> None:
    from sqlalchemy import text

    from opspilot.llm.providers.anthropic import anthropic_enabled
    from opspilot.persistence.db import create_engine, create_session_factory, get_database_url
    from opspilot.persistence.repositories import oauth_credentials

    if anthropic_enabled():
        _die("anthropic_enabled")
    for key in ("OPSPILOT_FORCE_RULES", "FORCE_RULES", "OPSPILOT_LLM_DISABLE", "LLM_DISABLE"):
        if os.environ.get(key, "").strip().lower() in {"1", "true", "yes", "on"}:
            _die("force_rules_or_llm_disable")

    allow_raw = os.environ.get("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "").strip()
    allow_parts = [p.strip().lower() for p in allow_raw.split(",") if p.strip()]
    allow_ok = len(allow_parts) == 1 and allow_parts[0] == operator
    print(f"allowlist_exact_one={_yn(len(allow_parts) == 1)}")
    print(f"allowlist_matches_operator={_yn(allow_ok)}")
    if not allow_ok:
        _die("allowlist_must_be_exactly_operator_email")

    # Alembic head: compare DB revision id to repo script head (ids only).
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    repo_head = script.get_current_head()
    engine = create_engine(get_database_url())
    sf = create_session_factory(engine)
    with sf() as session:
        db_head = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        cred = oauth_credentials.get_decrypted_refresh(session, provider="google")
        scopes = ""
        if cred is not None:
            from sqlalchemy import select

            from opspilot.persistence.models import OAuthCredentialRow

            row = session.scalars(
                select(OAuthCredentialRow).where(OAuthCredentialRow.provider == "google")
            ).one_or_none()
            scopes = (row.scopes if row is not None else "") or ""
    print(f"alembic_repo_head={repo_head}")
    print(f"alembic_db_head={db_head}")
    if str(db_head or "") != str(repo_head or ""):
        _die(f"alembic_head_mismatch repo={repo_head} db={db_head}")
    has_send = "gmail.send" in scopes
    print(f"gmail_send_scope={_yn(has_send)}")
    if not has_send:
        _die("gmail_send_scope=N")


def _load_operator_email() -> str:
    from opspilot.persistence.db import create_engine, create_session_factory, get_database_url
    from opspilot.persistence.repositories import oauth_credentials
    from opspilot.services.mail_address import MailAddressError

    engine = create_engine(get_database_url())
    sf = create_session_factory(engine)
    with sf() as session:
        cred = oauth_credentials.get_decrypted_refresh(session, provider="google")
    if cred is None:
        _die("no_operator_google_credential")
    email, _refresh = cred
    try:
        return _normalize_addr(email)
    except MailAddressError:
        _die("operator_email_invalid")


def _issue_cookie(email: str) -> str:
    from opspilot.services.operator_session import COOKIE_NAME, issue_session

    token = issue_session(email=email)
    print(f"operator_session_minted={_yn(bool(token))} cookie_name={COOKIE_NAME}")
    return token


def _phase_env(*, demo: str, allowlist: str) -> dict[str, str]:
    env = os.environ.copy()
    env["OPSPILOT_DEMO_MODE"] = demo
    env["OPSPILOT_SEND_RECIPIENT_ALLOWLIST"] = allowlist
    for k in ("OPSPILOT_FORCE_RULES", "OPSPILOT_LLM_DISABLE", "OPSPILOT_CSRF_RELAX_DEV", "FORCE_RULES", "LLM_DISABLE"):
        env.pop(k, None)
    return env


def _new_api_log_path() -> Path:
    API_LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = API_LOG_DIR / f"api-{stamp}-{uuid.uuid4().hex[:8]}.log"
    return path


def _start_api(env: dict[str, str], *, log_path: Path) -> subprocess.Popen[str]:
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
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(log_path, "a", encoding="utf-8")  # noqa: SIM115 — kept open for child lifetime
    print(f"api_log={log_path.relative_to(ROOT).as_posix()}")
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # Attach handle so _stop can close it after the child exits.
    proc._smoke_log_fh = log_fh  # type: ignore[attr-defined]
    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            _close_api_log(proc)
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


def _close_api_log(proc: subprocess.Popen[str] | None) -> None:
    if proc is None:
        return
    fh = getattr(proc, "_smoke_log_fh", None)
    if fh is not None:
        try:
            fh.close()
        except Exception:
            pass
        try:
            delattr(proc, "_smoke_log_fh")
        except Exception:
            pass


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
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
    _close_api_log(proc)


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


@dataclass(frozen=True)
class SelfSentTarget:
    work_item_id: str
    self_sent_count: int


def select_self_sent_gmail_target(*, operator: str) -> SelfSentTarget:
    """Read-only: most recent gmail WI whose normalized sender equals operator.

    Uses product ``parse_single_addr_spec``. Never prints addresses or subjects.
    """
    from sqlalchemy import text

    from opspilot.persistence.db import create_engine, create_session_factory, get_database_url
    from opspilot.services.mail_address import MailAddressError

    engine = create_engine(get_database_url())
    sf = create_session_factory(engine)
    with sf() as session:
        rows = session.execute(
            text(
                """
                SELECT id, sender_or_requester
                FROM work_items
                WHERE source_type = 'gmail'
                ORDER BY received_at DESC NULLS LAST
                """
            )
        ).all()

    matches: list[str] = []
    for wid, sender in rows:
        try:
            if _normalize_addr(str(sender or "")) == operator:
                matches.append(str(wid))
        except MailAddressError:
            continue

    count = len(matches)
    print(f"target_self_sent_item={_yn(count > 0)} self_sent_items={count}")
    if count == 0:
        _die(FAIL_NO_SELF_SENT)
    # First match is most recent (ORDER BY received_at DESC).
    return SelfSentTarget(work_item_id=matches[0], self_sent_count=count)


@dataclass(frozen=True)
class DraftRow:
    draft_id: str
    work_item_id: str | None
    to_addrs: str
    payload_sha256: str
    status: str


def _load_draft_row(draft_id: str) -> DraftRow:
    """Read-only SELECT of draft fields needed for the gate (no GET route exists)."""
    from sqlalchemy import text

    from opspilot.persistence.db import create_engine, create_session_factory, get_database_url

    engine = create_engine(get_database_url())
    sf = create_session_factory(engine)
    with sf() as session:
        row = session.execute(
            text(
                """
                SELECT id, work_item_id, to_addrs, payload_sha256, status
                FROM mail_drafts
                WHERE id = :id
                """
            ),
            {"id": draft_id},
        ).one_or_none()
    if row is None:
        _die("draft_missing")
    return DraftRow(
        draft_id=str(row[0]),
        work_item_id=str(row[1]) if row[1] is not None else None,
        to_addrs=str(row[2] or ""),
        payload_sha256=str(row[3]),
        status=str(row[4]),
    )


def _recipient_list(to_addrs: str) -> list[str]:
    """Return normalized addr-specs from a draft to_addrs field (may be multi)."""
    from email.utils import getaddresses

    from opspilot.services.mail_address import MailAddressError

    parsed = getaddresses([to_addrs or ""])
    out: list[str] = []
    for _display, addr in parsed:
        addr = (addr or "").strip()
        if not addr:
            continue
        try:
            out.append(_normalize_addr(addr))
        except MailAddressError:
            # Unparseable fragment still counts as a recipient slot for the gate.
            out.append(addr.lower())
    return out


def verify_draft_for_operator(
    *,
    draft_id: str,
    expected_work_item_id: str,
    operator: str,
) -> DraftRow:
    """Exit before approve unless draft targets the selected self-sent item + operator recip."""
    row = _load_draft_row(draft_id)
    if row.work_item_id != expected_work_item_id:
        _die(FAIL_DRAFT_WRONG_ITEM)
    recips = _recipient_list(row.to_addrs)
    if len(recips) != 1:
        _die(FAIL_DRAFT_RECIPIENT_COUNT)
    if recips[0] != operator:
        _die(FAIL_DRAFT_RECIPIENT_NOT_OPERATOR)
    print("draft_item_matches=Y draft_recipient_is_operator=Y")
    return row


def _error_code_and_request_id(resp: httpx.Response) -> tuple[str, str]:
    """Extract codes/ids only — never message text."""
    err_code = ""
    request_id = (resp.headers.get("X-Request-ID") or "").strip()
    try:
        body = resp.json()
    except Exception:
        body = None
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            err_code = str(err.get("code") or "")
            if not request_id:
                rid = err.get("request_id")
                if isinstance(rid, str) and rid.strip():
                    request_id = rid.strip()
        elif isinstance(err, str) and err.strip():
            # legacy / alternate shapes
            err_code = err.strip()
        if not err_code:
            err_code = str(body.get("error_code") or "")
        detail = body.get("detail")
        if not err_code and isinstance(detail, dict):
            nested = detail.get("error")
            if isinstance(nested, str):
                err_code = nested
            elif isinstance(nested, dict):
                err_code = str(nested.get("code") or nested.get("error") or "")
    return err_code or "none", request_id or "none"


def _print_http_fail(kind: str, resp: httpx.Response) -> None:
    code, rid = _error_code_and_request_id(resp)
    print(f"approve_status={resp.status_code} error_code={code} request_id={rid}")
    # ``kind`` distinguishes sync/ask/approve in FAIL line without dumping bodies.
    _die(f"{kind}_failed")


def _ask_draft(
    client: httpx.Client,
    *,
    asks_used: list[int],
    work_item_id: str,
) -> dict[str, Any]:
    if asks_used[0] >= SMOKE_MAX_ASKS:
        _die("llm_ask_cap")
    asks_used[0] += 1
    print(f"llm_asks_used={asks_used[0]} max={SMOKE_MAX_ASKS}")
    question = ask_prompt_for_work_item(work_item_id)
    with client.stream(
        "POST",
        "/api/v1/ask/stream",
        json={"question": question},
    ) as resp:
        if resp.status_code != 200:
            code, rid = _error_code_and_request_id(resp)
            print(f"approve_status={resp.status_code} error_code={code} request_id={rid}")
            _die("ask_stream_failed")
        draft: dict[str, Any] | None = None
        for line in resp.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = json.loads(line[5:].strip() or "{}")
            if payload.get("type") == "draft":
                draft = payload.get("data") or payload
            if payload.get("type") in {"final", "error"}:
                if payload.get("type") == "error" and not draft:
                    code = str(payload.get("code") or "ask_error")
                    rid = str(payload.get("request_id") or "none")
                    print(f"approve_status=200 error_code={code} request_id={rid}")
                    _die("ask_stream_failed")
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


def _create_verified_draft(
    client: httpx.Client,
    *,
    asks_used: list[int],
    target: SelfSentTarget,
    operator: str,
) -> DraftRow:
    draft = _ask_draft(client, asks_used=asks_used, work_item_id=target.work_item_id)
    draft_id = str(draft["draft_id"])
    return verify_draft_for_operator(
        draft_id=draft_id,
        expected_work_item_id=target.work_item_id,
        operator=operator,
    )


def assert_script_has_no_sql_writes(source: str) -> None:
    """Hermetic guard: SQL passed to ``text(...)`` must be SELECT-only."""
    # Only inspect sqlalchemy text() string literals (avoids create_engine false positives).
    for match in re.finditer(
        r"text\s*\(\s*(?:\"\"\"(.*?)\"\"\"|'''(.*?)'''|\"(.*?)\"|'(.*?)')",
        source,
        flags=re.DOTALL,
    ):
        groups = [g for g in match.groups() if g is not None]
        if not groups:
            continue
        sql = groups[0]
        if _SQL_WRITE_RE.search(sql):
            raise AssertionError("live_smoke_b5.py SQL must not contain write keywords")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="B5 live smoke (operator-gated)")
    parser.add_argument(
        "--send",
        action="store_true",
        help="Allow at most one real Gmail send (default: no send)",
    )
    args = parser.parse_args(argv)
    mode = "send" if args.send else "default"
    print(f"mode={mode}")
    print(f"database_host={_host_label()}")
    print("live_smoke_b5 start (not for CI)")

    operator = _load_operator_email()
    _preflight(operator=operator)

    cookie = _issue_cookie(operator)
    before = _count_sql()
    _print_counts("before", before)

    sends = 0
    asks_used = [0]
    proc: subprocess.Popen[str] | None = None
    api_log = _new_api_log_path()
    target: SelfSentTarget | None = None
    draft_row: DraftRow | None = None
    try:
        print("phase=sync_and_draft")
        proc = _start_api(_phase_env(demo="0", allowlist=operator), log_path=api_log)
        with _client(cookie) as client:
            sync = client.post(SYNC_PATH)
            print(f"sync_status={sync.status_code}")
            if sync.status_code != 200:
                _print_http_fail("sync", sync)

            target = select_self_sent_gmail_target(operator=operator)
            draft_row = _create_verified_draft(client, asks_used=asks_used, target=target, operator=operator)
            draft_id = draft_row.draft_id
            sha = draft_row.payload_sha256

            if args.send:
                key_a = str(uuid.uuid4())
                resp = _approve(client, draft_id, sha, key_a)
                print(f"approve_send_status={resp.status_code}")
                err_code, _rid = _error_code_and_request_id(resp)
                if resp.status_code == 502 or err_code == "send_outcome_unknown":
                    print("send_outcome_unknown=Y")
                    sends = 1
                    print(f"real_sends={sends}")
                    print("expect_409=skipped")
                elif resp.status_code != 200:
                    _print_http_fail("approve_send", resp)
                else:
                    sends = 1
                    print(f"real_sends={sends}")
                    resp_409 = _approve(client, draft_id, sha, str(uuid.uuid4()))
                    print(f"reapprove_status={resp_409.status_code} expect_409={_yn(resp_409.status_code == 409)}")
                    if resp_409.status_code != 409:
                        _print_http_fail("reapprove", resp_409)
                    resp_replay = _approve(client, draft_id, sha, key_a)
                    replay_body = resp_replay.json()
                    replay_ok = (
                        resp_replay.status_code == 200
                        and isinstance(replay_body, dict)
                        and replay_body.get("status") == "idempotent_replay"
                    )
                    print(f"idempotent_replay={_yn(replay_ok)}")
                    if not replay_ok:
                        _print_http_fail("idempotent_replay", resp_replay)
            else:
                print("expect_409=skipped")
        _stop(proc)
        proc = None

        assert target is not None and draft_row is not None

        print("phase=demo")
        # DEMO_MODE 403 proves the gate itself: draft recipient is still the operator
        # (verified), so the 403 cannot be explained by a third-party allowlist miss.
        proc = _start_api(_phase_env(demo="1", allowlist=operator), log_path=api_log)
        with _client(cookie) as client:
            sha = draft_row.payload_sha256
            draft_id = draft_row.draft_id
            resp = _approve(client, draft_id, sha, str(uuid.uuid4()))
            # After a successful send the draft is sent → 409; mint a fresh verified draft.
            if resp.status_code == 409 and args.send:
                draft_row = _create_verified_draft(client, asks_used=asks_used, target=target, operator=operator)
                draft_id = draft_row.draft_id
                sha = draft_row.payload_sha256
                resp = _approve(client, draft_id, sha, str(uuid.uuid4()))
            print(f"demo_approve_status={resp.status_code} expect_403={_yn(resp.status_code == 403)}")
            if resp.status_code != 403:
                _print_http_fail("demo_approve", resp)
        _stop(proc)
        proc = None

        print("phase=allowlist_empty")
        # Empty allowlist deny-all is still a valid gate proof when the draft's only
        # recipient IS the operator: recipients_allowed fails because allow is None /
        # empty, not because the address is third-party. That isolates the allowlist
        # mechanism from "wrong recipient" failures.
        proc = _start_api(_phase_env(demo="0", allowlist=""), log_path=api_log)
        with _client(cookie) as client:
            sha = draft_row.payload_sha256
            draft_id = draft_row.draft_id
            resp = _approve(client, draft_id, sha, str(uuid.uuid4()))
            if resp.status_code == 409:
                draft_row = _create_verified_draft(client, asks_used=asks_used, target=target, operator=operator)
                draft_id = draft_row.draft_id
                sha = draft_row.payload_sha256
                resp = _approve(client, draft_id, sha, str(uuid.uuid4()))
            print(f"empty_allowlist_status={resp.status_code} expect_403={_yn(resp.status_code == 403)}")
            if resp.status_code != 403:
                _print_http_fail("empty_allowlist", resp)
        _stop(proc)
        proc = None

        after = _count_sql()
        _print_counts("after", after)
        print(f"delta_mail_send_audit={after['mail_send_audit'] - before['mail_send_audit']}")
        print(f"real_sends_total={sends}")
        print(f"llm_asks_used={asks_used[0]} max={SMOKE_MAX_ASKS}")
        if args.send and sends != 1:
            _die("expected_exactly_one_real_send")
        if not args.send and sends != 0:
            _die("default_mode_must_not_send")
        print("live_smoke_b5=PASS")
    finally:
        _stop(proc)


if __name__ == "__main__":
    main()
