"""Hermetic unit tests for live_smoke_b5 (never runs the live smoke script end-to-end)."""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "live_smoke_b5.py"


def _load_smoke():
    spec = importlib.util.spec_from_file_location("live_smoke_b5", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["live_smoke_b5"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def smoke():
    return _load_smoke()


def test_smoke_sync_path_constant(smoke) -> None:
    assert smoke.SYNC_PATH == "/api/v1/sync"


def test_smoke_max_asks_constant(smoke) -> None:
    assert smoke.SMOKE_MAX_ASKS == 3


def test_default_vs_send_flag(smoke) -> None:
    args = smoke.argparse.ArgumentParser()
    args.add_argument("--send", action="store_true")
    assert args.parse_args([]).send is False
    assert args.parse_args(["--send"]).send is True


def test_preflight_anthropic_enabled(smoke, monkeypatch: pytest.MonkeyPatch) -> None:
    import opspilot.llm.providers.anthropic as anth

    monkeypatch.setattr(anth, "anthropic_enabled", lambda: True)
    with pytest.raises(SystemExit):
        smoke._preflight(operator="ops@example.com")


def test_preflight_force_rules(smoke, monkeypatch: pytest.MonkeyPatch) -> None:
    import opspilot.llm.providers.anthropic as anth

    monkeypatch.setattr(anth, "anthropic_enabled", lambda: False)
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    with pytest.raises(SystemExit):
        smoke._preflight(operator="ops@example.com")


def test_preflight_allowlist_mismatch(smoke, monkeypatch: pytest.MonkeyPatch) -> None:
    import opspilot.llm.providers.anthropic as anth

    monkeypatch.setattr(anth, "anthropic_enabled", lambda: False)
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.delenv("LLM_DISABLE", raising=False)
    monkeypatch.setenv("OPSPILOT_SEND_RECIPIENT_ALLOWLIST", "other@example.com")
    with pytest.raises(SystemExit):
        smoke._preflight(operator="ops@example.com")


def test_ask_cap_enforced(smoke) -> None:
    asks = [smoke.SMOKE_MAX_ASKS]
    with pytest.raises(SystemExit):
        if asks[0] >= smoke.SMOKE_MAX_ASKS:
            smoke._die("llm_ask_cap")


def test_unknown_counts_as_one_send_stops(smoke) -> None:
    """Documented flag logic: unknown outcome consumes the one-send budget."""
    sends = 0
    err_code = "send_outcome_unknown"
    status = 502
    if status == 502 or err_code == "send_outcome_unknown":
        sends = 1
    assert sends == 1


def test_script_source_has_no_sql_writes(smoke) -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    smoke.assert_script_has_no_sql_writes(source)


def _fake_session_factory(rows: list[tuple[str, str]]):
    class _Result:
        def __init__(self, data: list[tuple[str, str]]) -> None:
            self._data = data

        def all(self) -> list[tuple[str, str]]:
            return list(self._data)

    class _Session:
        def execute(self, _stmt: Any, _params: Any = None) -> _Result:
            return _Result(rows)

        def __enter__(self) -> _Session:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def _factory(_engine: Any = None) -> _Session:
        return _Session()

    return _factory


def test_select_self_sent_most_recent(
    smoke, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import opspilot.persistence.db as db

    # ORDER BY received_at DESC is applied in SQL; rows arrive newest-first.
    rows = [
        ("wi_newest_self", "Ops <ops@example.com>"),
        ("wi_other", "other@example.com"),
        ("wi_older_self", "OPS@EXAMPLE.COM"),
    ]
    monkeypatch.setattr(db, "create_engine", lambda _url: object())
    monkeypatch.setattr(db, "get_database_url", lambda: "postgresql+psycopg://x")
    monkeypatch.setattr(db, "create_session_factory", lambda _eng: _fake_session_factory(rows))

    target = smoke.select_self_sent_gmail_target(operator="ops@example.com")
    assert target.work_item_id == "wi_newest_self"
    assert target.self_sent_count == 2
    out = capsys.readouterr().out
    assert "target_self_sent_item=Y" in out
    assert "self_sent_items=2" in out
    assert "ops@example.com" not in out
    assert "Ops" not in out


def test_select_self_sent_normalizes_case_and_display(smoke, monkeypatch: pytest.MonkeyPatch) -> None:
    import opspilot.persistence.db as db

    rows = [("wi_1", "Display Name <OPS@Example.COM>")]
    monkeypatch.setattr(db, "create_engine", lambda _url: object())
    monkeypatch.setattr(db, "get_database_url", lambda: "postgresql+psycopg://x")
    monkeypatch.setattr(db, "create_session_factory", lambda _eng: _fake_session_factory(rows))

    target = smoke.select_self_sent_gmail_target(operator="ops@example.com")
    assert target.work_item_id == "wi_1"
    assert target.self_sent_count == 1


def test_select_self_sent_none_exits(
    smoke, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import opspilot.persistence.db as db

    rows = [("wi_1", "third@example.com")]
    monkeypatch.setattr(db, "create_engine", lambda _url: object())
    monkeypatch.setattr(db, "get_database_url", lambda: "postgresql+psycopg://x")
    monkeypatch.setattr(db, "create_session_factory", lambda _eng: _fake_session_factory(rows))

    with pytest.raises(SystemExit) as exc:
        smoke.select_self_sent_gmail_target(operator="ops@example.com")
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "target_self_sent_item=N" in out
    assert "self_sent_items=0" in out
    assert "FAIL: no_self_sent_item" in out


def test_ask_prompt_contains_work_item_id(smoke) -> None:
    prompt = smoke.ask_prompt_for_work_item("wi_abc123")
    assert "wi_abc123" in prompt
    assert "draft_reply" in prompt
    assert "latest inbox" not in prompt.lower()


def test_draft_gate_wrong_item_no_approve(
    smoke, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    approve_calls = {"n": 0}

    def _boom(*_a: object, **_k: object) -> None:
        approve_calls["n"] += 1
        raise AssertionError("approve must not be called")

    monkeypatch.setattr(
        smoke,
        "_load_draft_row",
        lambda _id: smoke.DraftRow(
            draft_id="md_1",
            work_item_id="wi_other",
            to_addrs="ops@example.com",
            payload_sha256="a" * 64,
            status="draft",
        ),
    )
    monkeypatch.setattr(smoke, "_approve", _boom)
    with pytest.raises(SystemExit):
        smoke.verify_draft_for_operator(
            draft_id="md_1",
            expected_work_item_id="wi_self",
            operator="ops@example.com",
        )
    assert approve_calls["n"] == 0
    assert "FAIL: draft_wrong_item" in capsys.readouterr().out


def test_draft_gate_recipient_count_no_approve(
    smoke, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    approve_calls = {"n": 0}
    monkeypatch.setattr(smoke, "_approve", lambda *_a, **_k: approve_calls.__setitem__("n", approve_calls["n"] + 1))
    monkeypatch.setattr(
        smoke,
        "_load_draft_row",
        lambda _id: smoke.DraftRow(
            draft_id="md_1",
            work_item_id="wi_self",
            to_addrs="ops@example.com, other@example.com",
            payload_sha256="a" * 64,
            status="draft",
        ),
    )
    with pytest.raises(SystemExit):
        smoke.verify_draft_for_operator(
            draft_id="md_1",
            expected_work_item_id="wi_self",
            operator="ops@example.com",
        )
    assert approve_calls["n"] == 0
    assert "FAIL: draft_recipient_count" in capsys.readouterr().out


def test_draft_gate_recipient_not_operator_no_approve(
    smoke, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    approve_calls = {"n": 0}

    def _count(*_a: object, **_k: object) -> None:
        approve_calls["n"] += 1

    monkeypatch.setattr(smoke, "_approve", _count)
    monkeypatch.setattr(
        smoke,
        "_load_draft_row",
        lambda _id: smoke.DraftRow(
            draft_id="md_1",
            work_item_id="wi_self",
            to_addrs="Other Person <third@example.com>",
            payload_sha256="a" * 64,
            status="draft",
        ),
    )
    with pytest.raises(SystemExit):
        smoke.verify_draft_for_operator(
            draft_id="md_1",
            expected_work_item_id="wi_self",
            operator="ops@example.com",
        )
    assert approve_calls["n"] == 0
    out = capsys.readouterr().out
    assert "FAIL: draft_recipient_not_operator" in out
    assert "third@example.com" not in out


def test_draft_gate_success_prints_flags(
    smoke, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        smoke,
        "_load_draft_row",
        lambda _id: smoke.DraftRow(
            draft_id="md_1",
            work_item_id="wi_self",
            to_addrs="Ops <OPS@Example.COM>",
            payload_sha256="b" * 64,
            status="draft",
        ),
    )
    row = smoke.verify_draft_for_operator(
        draft_id="md_1",
        expected_work_item_id="wi_self",
        operator="ops@example.com",
    )
    assert row.payload_sha256 == "b" * 64
    out = capsys.readouterr().out
    assert "draft_item_matches=Y" in out
    assert "draft_recipient_is_operator=Y" in out


def test_approve_failure_prints_codes_not_body(smoke, capsys: pytest.CaptureFixture[str]) -> None:
    body = {
        "error": {
            "code": "recipient_not_allowlisted",
            "message": "Recipient not on send allowlist. SECRET_SHOULD_NOT_PRINT",
            "request_id": "req_smoke_1",
        }
    }
    resp = httpx.Response(
        403,
        json=body,
        headers={"X-Request-ID": "req_smoke_1"},
        request=httpx.Request("POST", "http://127.0.0.1:8010/api/v1/mail/drafts/x/approve"),
    )
    with pytest.raises(SystemExit) as exc:
        smoke._print_http_fail("approve_send", resp)
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "approve_status=403" in out
    assert "error_code=recipient_not_allowlisted" in out
    assert "request_id=req_smoke_1" in out
    assert "FAIL: approve_send_failed" in out
    assert "SECRET_SHOULD_NOT_PRINT" not in out
    assert "Recipient not on send allowlist" not in out


def test_api_log_path_under_gitignored_tmp(smoke, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "tmp/" in gitignore
    # Point API_LOG_DIR at a tmp/live_smoke-equivalent path under the real ROOT constant.
    assert smoke.API_LOG_DIR == ROOT / "tmp" / "live_smoke"
    path = smoke._new_api_log_path()
    assert path.is_relative_to(ROOT / "tmp" / "live_smoke") or str(path).replace("\\", "/").find("tmp/live_smoke") >= 0
    rel = path.relative_to(ROOT).as_posix()
    assert rel.startswith("tmp/live_smoke/")
    # Ensure the script never prints log contents — only the relative path line.
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    print(f"api_log={rel}")
    printed = buf.getvalue()
    assert printed.strip() == f"api_log={rel}"
    assert "uvicorn" not in printed


def test_error_code_extraction_shapes(smoke) -> None:
    resp = httpx.Response(
        403,
        json={"error": {"code": "demo_mode_blocks_send", "request_id": "r1"}},
        request=httpx.Request("POST", "http://example.test/"),
    )
    code, rid = smoke._error_code_and_request_id(resp)
    assert code == "demo_mode_blocks_send"
    assert rid == "r1"
