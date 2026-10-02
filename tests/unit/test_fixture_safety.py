"""Fail if committed Google/LLM fixtures look like real PII or tokens."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GOOGLE = ROOT / "fixtures" / "google"
LLM = ROOT / "fixtures" / "llm_turns"

ALLOWED_EMAIL_SUFFIXES = ("@example.test", "@example.com")
ALLOWED_SUBJECTS = frozenset({"FIXTURE_SUBJECT", "Re: FIXTURE_SUBJECT"})
ALLOWED_BODIES = frozenset({"FIXTURE_BODY", ""})
TOKEN_RE = re.compile(r"(ya29\.|Bearer\s+|1//|refresh_token)", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _iter_fixture_files() -> list[Path]:
    files: list[Path] = []
    if GOOGLE.is_dir():
        files.extend(sorted(GOOGLE.glob("*.json")))
    if LLM.is_dir():
        files.extend(sorted(LLM.glob("*.json")))
    return files


def test_fixture_dirs_exist_with_expected_files() -> None:
    assert (GOOGLE / "history.json").is_file()
    assert (GOOGLE / "message.json").is_file()
    assert (GOOGLE / "calendar.json").is_file()
    assert (GOOGLE / "token_error.json").is_file()
    assert (LLM / "empty_args.json").is_file()
    assert (LLM / "draft_reply.json").is_file()


@pytest.mark.parametrize("path", _iter_fixture_files(), ids=lambda p: p.name)
def test_fixture_safety(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert TOKEN_RE.search(text) is None, f"token-like string in {path.name}"

    data = json.loads(text)
    blob = json.dumps(data)

    for email in EMAIL_RE.findall(blob):
        assert email.lower().endswith(ALLOWED_EMAIL_SUFFIXES), f"non-fictional email in {path.name}: redacted"

    # Opaque id gate: require fx_ prefix on gmail/calendar shaped id fields.
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
                if node.startswith("<") and node.endswith("@"):
                    return
                if "@example.test>" in node or node.endswith("@example.test>"):
                    return
                if node.startswith("<") and "@example.test>" in node:
                    return
                if not node.startswith("fx_"):
                    raise AssertionError(f"unsanitized id field {key} in {path.name}")

        check_ids(data)

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                key = str(k).lower()
                if key in {"subject", "summary"} and isinstance(v, str):
                    assert v in ALLOWED_SUBJECTS or v.startswith("fx_"), f"subject not allowlisted in {path.name}"
                if key in {"body", "description", "snippet", "error_description"} and isinstance(v, str):
                    assert v in ALLOWED_BODIES or v == "invalid_grant", f"body not allowlisted in {path.name}"
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)


def test_google_fixtures_load_as_json() -> None:
    for name in ("history.json", "message.json", "calendar.json", "token_error.json"):
        payload = json.loads((GOOGLE / name).read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
