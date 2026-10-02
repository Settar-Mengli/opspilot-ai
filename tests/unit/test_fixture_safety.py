"""Fail if committed fixtures look like real PII or tokens."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_llm_turn_fixtures_have_expected_kinds() -> None:
    empty = json.loads((LLM / "empty_args.json").read_text(encoding="utf-8"))
    draft = json.loads((LLM / "draft_reply.json").read_text(encoding="utf-8"))
    assert empty.get("tool") == "draft_reply"
    assert empty.get("args") == {}
    assert draft.get("tool") == "draft_reply"
    assert draft.get("args", {}).get("work_item_id", "").startswith("fx_")


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
