"""Fail if committed fixtures look like real PII or tokens."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
GOOGLE = FIXTURES / "google"
LLM = FIXTURES / "llm_turns"
REPO = ROOT.parent
CAPTURE = REPO / "scripts" / "capture_google_fixtures.py"

# Strict allowlists for Google + llm_turns captures.
ALLOWED_EMAIL_SUFFIXES_STRICT = ("@example.test", "@example.com")
ALLOWED_SUBJECTS_STRICT = frozenset({"FIXTURE_SUBJECT", "Re: FIXTURE_SUBJECT"})
ALLOWED_BODIES_STRICT = frozenset({"FIXTURE_BODY", "", "invalid_grant"})

# Vertical-slice / history fixtures: token scan still applies; email/subject/body use this list.
ALLOWED_EMAIL_SUFFIXES_SLICE = ("@example.test", "@example.com", "@company.local")
# subject_or_title / free-form briefing text allowed on exempted paths only.
_SLICE_SUBJECT_OK = re.compile(r"^[\w\s:./#'()+,!-]+$", re.I)

TOKEN_RE = re.compile(r"(ya29\.|Bearer\s+|1//|refresh_token)", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


@pytest.fixture()
def allow_llm_fixture_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable LLM path for fixture-driven agent loop tests (FORCE_RULES off)."""
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    for provider in ("GEMINI", "GROQ", "MISTRAL", "CLOUDFLARE", "OPENROUTER"):
        monkeypatch.setenv(f"OPSPILOT_BUDGET_{provider}_REQ_DAY", "100")
        monkeypatch.setenv(f"OPSPILOT_BUDGET_{provider}_TOK_DAY", "100000")
    monkeypatch.setenv("OPSPILOT_ASK_MAX_STEPS", "5")
    monkeypatch.setenv("OPSPILOT_ASK_MAX_PROVIDER_CALLS", "8")


def _is_slice_path(path: Path) -> bool:
    rel = path.relative_to(FIXTURES).as_posix()
    return rel == "sample_input.json" or rel.startswith("history/")


def _iter_all_fixture_files() -> list[Path]:
    if not FIXTURES.is_dir():
        return []
    return sorted(p for p in FIXTURES.rglob("*") if p.is_file())


def test_fixture_dirs_exist_with_expected_files() -> None:
    assert (GOOGLE / "history.json").is_file()
    assert (GOOGLE / "message.json").is_file()
    assert (GOOGLE / "calendar.json").is_file()
    assert (GOOGLE / "token_error.json").is_file()
    assert (LLM / "empty_args.json").is_file()
    assert (LLM / "draft_reply.json").is_file()


@pytest.mark.parametrize("path", _iter_all_fixture_files(), ids=lambda p: p.relative_to(FIXTURES).as_posix())
def test_fixture_safety(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    # Token/secret patterns: no exemptions (A6).
    assert TOKEN_RE.search(text) is None, f"token-like string in {path}"

    slice_path = _is_slice_path(path)
    email_suffixes = ALLOWED_EMAIL_SUFFIXES_SLICE if slice_path else ALLOWED_EMAIL_SUFFIXES_STRICT

    # Non-JSON files: still scan emails in raw text.
    if path.suffix.lower() != ".json":
        for email in EMAIL_RE.findall(text):
            assert email.lower().endswith(email_suffixes), f"non-fictional email in {path}"
        return

    data = json.loads(text)
    blob = json.dumps(data)
    for email in EMAIL_RE.findall(blob):
        assert email.lower().endswith(email_suffixes), f"non-fictional email in {path}"

    if path.parent.name == "google":

        def check_ids(node: object, key: str | None = None) -> None:
            id_keys = {"id", "threadid", "historyid", "nextsynctoken", "message-id"}
            if isinstance(node, dict):
                for k, v in node.items():
                    check_ids(v, str(k).lower())
            elif isinstance(node, list):
                for item in node:
                    check_ids(item, key)
            elif isinstance(node, str) and key in id_keys:
                if node.startswith("<") and "@example.test>" in node:
                    return
                if not node.startswith("fx_"):
                    raise AssertionError(f"unsanitized id field {key} in {path.name}")

        check_ids(data)

    subject_keys = {"subject", "summary", "subject_or_title"}
    body_keys = {"body", "description", "snippet", "body_or_description", "error_description"}

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                key = str(k).lower()
                if key in subject_keys and isinstance(v, str) and v:
                    if slice_path:
                        assert _SLICE_SUBJECT_OK.match(v), f"subject not allowlisted in {path}"
                    else:
                        assert v in ALLOWED_SUBJECTS_STRICT or v.startswith("fx_"), (
                            f"subject not allowlisted in {path.name}"
                        )
                if key in body_keys and isinstance(v, str):
                    if slice_path:
                        assert len(v) < 2000, f"body too large in {path}"
                    else:
                        assert v in ALLOWED_BODIES_STRICT or v == "invalid_grant", (
                            f"body not allowlisted in {path.name}"
                        )
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)


def test_google_fixtures_load_as_json() -> None:
    for name in ("history.json", "message.json", "calendar.json", "token_error.json"):
        payload = json.loads((GOOGLE / name).read_text(encoding="utf-8"))
        assert isinstance(payload, dict)


def test_fixture_history_json_drives_history_message_ids() -> None:
    from opspilot.integrations.gmail_client import GmailClient

    payload = json.loads((GOOGLE / "history.json").read_text(encoding="utf-8"))

    class _Tx:
        def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
            assert "/history" in url
            return __import__("httpx").Response(200, json=payload)

    added, removed, truncated, last_hid = GmailClient(access_token="t", transport=_Tx()).history_message_ids(
        start_history_id="fx_hid_0001"
    )
    assert "fx_msg_aaa111" in added
    assert "fx_msg_ccc333" in removed
    assert "fx_msg_bbb222" in removed  # SPAM labelAdded
    assert truncated is False
    assert last_hid == "fx_hid_0004"


def test_fixture_message_json_parses() -> None:
    from opspilot.integrations.gmail_client import parse_message

    payload = json.loads((GOOGLE / "message.json").read_text(encoding="utf-8"))
    msg = parse_message(payload)
    assert msg.provider_id == "fx_msg_aaa111"
    assert msg.subject == "FIXTURE_SUBJECT"
    assert "FIXTURE_BODY" in msg.body or msg.body


def test_fixture_calendar_json_lists_event() -> None:
    from datetime import UTC, datetime, timedelta

    from opspilot.integrations.calendar_client import CalendarClient

    payload = json.loads((GOOGLE / "calendar.json").read_text(encoding="utf-8"))

    class _Tx:
        def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
            return __import__("httpx").Response(200, json=payload)

    now = datetime.now(UTC)
    listed = CalendarClient(access_token="t", transport=_Tx()).list_events(
        time_min=now, time_max=now + timedelta(days=7)
    )
    assert listed.truncated is False
    assert any(ev.provider_id.startswith("fx_") for ev in listed.events)


def test_fixture_token_error_json_is_invalid_grant() -> None:
    payload = json.loads((GOOGLE / "token_error.json").read_text(encoding="utf-8"))
    assert payload.get("error") == "invalid_grant"


def test_fixture_token_error_drives_refresh_invalid_grant_no_retry() -> None:
    """token_error.json → refresh_access_token raises invalid_grant; single POST (no retry)."""
    import httpx

    from opspilot.integrations.google_http import GoogleHttpError, refresh_access_token

    payload = json.loads((GOOGLE / "token_error.json").read_text(encoding="utf-8"))
    calls = {"n": 0}

    class _Tx:
        def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
            calls["n"] += 1
            assert "oauth2.googleapis.com/token" in url
            return httpx.Response(400, json=payload)

    with pytest.raises(GoogleHttpError) as exc:
        refresh_access_token(
            client_id="cid",
            client_secret="csec",
            refresh_token="rt",
            transport=_Tx(),  # type: ignore[arg-type]
        )
    assert str(exc.value.args[0]) == "invalid_grant"
    assert calls["n"] == 1


def test_fixture_token_error_sync_path_google_reauth_required(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx
    from cryptography.fernet import Fernet

    from opspilot.persistence.repositories import oauth_credentials
    from opspilot.services import google_sync

    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        refresh_token_plaintext="rt",
        scopes="https://www.googleapis.com/auth/gmail.readonly",
    )
    db_session.commit()
    payload = json.loads((GOOGLE / "token_error.json").read_text(encoding="utf-8"))
    calls = {"token": 0}

    class _Tx:
        def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
            if "oauth2.googleapis.com/token" in url:
                calls["token"] += 1
                return httpx.Response(400, json=payload)
            raise AssertionError(f"unexpected {method} {url}")

    with pytest.raises(google_sync.GoogleReauthRequired):
        google_sync.run_sync(db_session, transport=_Tx(), providers=["gmail"])  # type: ignore[arg-type]
    assert calls["token"] == 1


def test_fixture_token_error_approve_path_google_reauth_required(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx
    from cryptography.fernet import Fernet

    from opspilot.persistence.repositories import mail_drafts, oauth_credentials, work_items
    from opspilot.services import mail_hitl

    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "demo@example.com")
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="ops@example.com",
        refresh_token_plaintext="rt",
        scopes="https://www.googleapis.com/auth/gmail.send",
    )
    wi = work_items.upsert_by_provider_id(
        db_session,
        provider_id="fx_msg_tokerr",
        source_type="gmail",
        subject_or_title="FIXTURE_SUBJECT",
        body_or_description="FIXTURE_BODY",
        sender_or_requester="demo@example.com",
        received_at=__import__("datetime").datetime(2026, 10, 1, 12, 0, tzinfo=__import__("datetime").UTC),
        thread_id="thr_tokerr",
    )
    draft = mail_drafts.create_draft(
        db_session,
        work_item_id=wi,
        thread_id="thr_tokerr",
        gmail_provider_id="fx_msg_tokerr",
        to_addrs="demo@example.com",
        subject="Re: FIXTURE_SUBJECT",
        body="FIXTURE_BODY",
        operator_email="ops@example.com",
        request_id="req-tokerr",
    )
    db_session.commit()
    payload = json.loads((GOOGLE / "token_error.json").read_text(encoding="utf-8"))
    calls = {"token": 0}

    class _Tx:
        def request(self, method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
            if "oauth2.googleapis.com/token" in url:
                calls["token"] += 1
                return httpx.Response(400, json=payload)
            raise AssertionError(f"unexpected {method} {url}")

    with pytest.raises(mail_hitl.MailHitlError) as exc:
        mail_hitl.approve_and_send(
            db_session,
            draft.id,
            expected_payload_sha256=draft.payload_sha256,
            operator_email="ops@example.com",
            request_id="req-tokerr",
            idempotency_key="tokerr-1",
            transport=_Tx(),  # type: ignore[arg-type]
        )
    assert exc.value.code == "google_reauth_required"
    assert calls["token"] == 1


def test_llm_turn_fixtures_have_expected_kinds() -> None:
    empty = json.loads((LLM / "empty_args.json").read_text(encoding="utf-8"))
    draft = json.loads((LLM / "draft_reply.json").read_text(encoding="utf-8"))
    assert empty.get("tool") == "draft_reply"
    assert empty.get("args") == {}
    assert draft.get("tool") == "draft_reply"
    assert draft.get("args", {}).get("work_item_id", "").startswith("fx_")


@pytest.mark.usefixtures("allow_llm_fixture_agent")
def test_llm_turn_draft_reply_fixture_drives_agent_draft_event(db_session: Session) -> None:
    """draft_reply.json fed through real agent loop → draft event with server-owned Re: subject."""
    from datetime import UTC, datetime

    from opspilot.agent.loop import run_ask_agent
    from opspilot.llm.providers.fake import FakeProvider
    from opspilot.llm.types import AttemptStatus, ProviderResult
    from opspilot.persistence.models import WorkItemRow

    turn = json.loads((LLM / "draft_reply.json").read_text(encoding="utf-8"))
    wi_id = str(turn["args"]["work_item_id"])
    db_session.add(
        WorkItemRow(
            id=wi_id,
            source_type="gmail",
            subject_or_title="FIXTURE_SUBJECT",
            body_or_description="FIXTURE_BODY",
            sender_or_requester="demo@example.com",
            received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
            tags=[],
            provider_id="fx_msg_draft_turn",
            thread_id="thr_fx_draft",
        )
    )
    db_session.commit()

    def _pr(payload: dict) -> ProviderResult:
        return ProviderResult(
            status=AttemptStatus.SUCCESS,
            text=json.dumps(payload),
            model="fake-v1",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1,
        )

    fake = FakeProvider(
        name="gemini",
        json_results=[
            _pr(turn),
            _pr({"kind": "final", "final": "Draft ready"}),
        ],
    )
    events = list(
        run_ask_agent(
            question="Draft a reply",
            session=db_session,
            request_id="req-fx-draft",
            gmail_only=True,
            providers=[fake],
            operator_email="ops@example.com",
        )
    )
    drafts = [e for e in events if e.type == "draft"]
    assert drafts, "expected draft SSE event from fixture turn"
    assert drafts[0].data.get("subject") == "Re: FIXTURE_SUBJECT"
    assert "FIXTURE_BODY" in str(drafts[0].data.get("body") or "")


@pytest.mark.usefixtures("allow_llm_fixture_agent")
def test_llm_turn_empty_args_fixture_schema_repair_then_ok(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """empty_args.json → tool_args_invalid failover; repaired turn succeeds without terminal invalid."""
    from datetime import UTC, datetime

    from opspilot.agent import loop as agent_loop
    from opspilot.agent.loop import run_ask_agent
    from opspilot.llm.providers.fake import FakeProvider
    from opspilot.llm.types import AttemptStatus, ProviderResult
    from opspilot.persistence.repositories import work_items

    empty = json.loads((LLM / "empty_args.json").read_text(encoding="utf-8"))
    wi = work_items.upsert_by_provider_id(
        db_session,
        provider_id="fx_msg_empty_args",
        source_type="gmail",
        subject_or_title="FIXTURE_SUBJECT",
        body_or_description="FIXTURE_BODY",
        sender_or_requester="demo@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        thread_id="thr_fx_empty",
    )
    db_session.commit()
    repaired = {
        "kind": "tool",
        "tool": "draft_reply",
        "args": {"work_item_id": wi, "body": "FIXTURE_BODY"},
    }
    logs: list[str] = []

    def _capture(msg: str, *args: object) -> None:
        logs.append(msg % args if args else msg)

    monkeypatch.setattr(agent_loop._logger, "info", _capture)

    def _pr(payload: dict) -> ProviderResult:
        return ProviderResult(
            status=AttemptStatus.SUCCESS,
            text=json.dumps(payload),
            model="fake-v1",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1,
        )

    prov_a = FakeProvider(name="gemini", json_results=[_pr(empty)])
    prov_b = FakeProvider(
        name="groq",
        json_results=[_pr(repaired), _pr({"kind": "final", "final": "ok"})],
    )
    events = list(
        run_ask_agent(
            question="Draft",
            session=db_session,
            request_id="req-fx-empty",
            gmail_only=True,
            providers=[prov_a, prov_b],
            operator_email="ops@example.com",
        )
    )
    assert events[-1].data.get("code") != "tool_args_invalid"
    assert any("reason=tool_args_invalid" in line for line in logs)
    assert any(e.type == "draft" for e in events)


def test_capture_google_fixtures_refuses_without_env() -> None:
    env = {k: v for k, v in __import__("os").environ.items() if k != "OPSPILOT_CAPTURE_FIXTURES"}
    env.pop("OPSPILOT_CAPTURE_FIXTURES", None)
    proc = subprocess.run(
        [sys.executable, str(CAPTURE)],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "OPSPILOT_CAPTURE_FIXTURES" in (proc.stderr + proc.stdout)


def test_capture_refuses_under_pytest_or_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    # Script must refuse when CI or PYTEST_CURRENT_TEST is set even with CAPTURE=1.
    monkeypatch.setenv("OPSPILOT_CAPTURE_FIXTURES", "1")
    monkeypatch.setenv("CI", "true")
    proc = subprocess.run(
        [sys.executable, str(CAPTURE)],
        cwd=str(REPO),
        env={**__import__("os").environ, "OPSPILOT_CAPTURE_FIXTURES": "1", "CI": "true"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def test_capture_refuses_when_only_pytest_current_test_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """CAPTURE=1, CI unset, PYTEST_CURRENT_TEST set → still refuse."""
    monkeypatch.setenv("OPSPILOT_CAPTURE_FIXTURES", "1")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/unit/test_fixture_safety.py::test_x")
    env = {
        k: v
        for k, v in __import__("os").environ.items()
        if k not in {"CI", "OPSPILOT_CAPTURE_FIXTURES", "PYTEST_CURRENT_TEST"}
    }
    env["OPSPILOT_CAPTURE_FIXTURES"] = "1"
    env["PYTEST_CURRENT_TEST"] = "tests/unit/test_fixture_safety.py::test_x"
    proc = subprocess.run(
        [sys.executable, str(CAPTURE)],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "pytest" in (proc.stderr + proc.stdout).lower() or "CI" in (proc.stderr + proc.stdout)
