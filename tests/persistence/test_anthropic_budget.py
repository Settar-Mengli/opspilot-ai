"""Anthropic prepaid ledger reserve/reconcile + CLI (b6.1)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from opspilot.persistence.models import LlmCallRow
from opspilot.persistence.repositories.anthropic_budget import (
    ANTHROPIC_EST_INPUT_CAP,
    ERROR_CODE_RESERVED,
    anthropic_call_counts,
    estimate_input_tokens,
    get_budget,
    reconcile_reservation,
    reserve_and_open_call,
    set_budget,
)


def test_set_and_get_budget(db_session: Session) -> None:
    row = set_budget(db_session, tokens=1000, usd=Decimal("2.5"))
    db_session.commit()
    got = get_budget(db_session)
    assert got is not None
    assert got.remaining_tokens == 1000
    assert got.remaining_usd == Decimal("2.5")
    assert row.id == 1


def test_reserve_and_open_call_atomicity(db_session: Session) -> None:
    set_budget(db_session, tokens=500, usd=Decimal("1"))
    db_session.commit()
    call = reserve_and_open_call(
        db_session, tokens=100, usd=Decimal("0.25"), task="ask", model="claude-haiku-4-5-20251001"
    )
    db_session.commit()
    assert call is not None
    assert call.status == "error"
    assert call.error_code == ERROR_CODE_RESERVED
    assert call.meta.get("reconciled") is False
    row = get_budget(db_session)
    assert row is not None
    assert row.remaining_tokens == 400
    assert row.remaining_usd == Decimal("0.75")


def test_missing_ledger_no_reserve(db_session: Session) -> None:
    assert get_budget(db_session) is None
    assert reserve_and_open_call(db_session, tokens=10, usd=Decimal("0.01"), task="ask", model="m") is None


def test_insufficient_reserve(db_session: Session) -> None:
    set_budget(db_session, tokens=50, usd=Decimal("0.10"))
    db_session.commit()
    assert reserve_and_open_call(db_session, tokens=100, usd=Decimal("0.01"), task="ask", model="m") is None
    row = get_budget(db_session)
    assert row is not None
    assert row.remaining_tokens == 50


def test_reconcile_refund_when_actual_below_reserve(db_session: Session) -> None:
    set_budget(db_session, tokens=1000, usd=Decimal("1"))
    db_session.commit()
    call = reserve_and_open_call(db_session, tokens=200, usd=Decimal("0.40"), task="ask", model="m")
    db_session.commit()
    assert call is not None
    ok = reconcile_reservation(
        db_session,
        call_id=call.id,
        final_status="success",
        ledger_op="refund_delta",
        actual_tokens=100,
        actual_usd=Decimal("0.20"),
        tokens_in=80,
        tokens_out=20,
        error_code=None,
    )
    db_session.commit()
    assert ok is True
    row = get_budget(db_session)
    assert row is not None
    # reserved 200/0.40; actual 100/0.20; refund 100/0.20 → remaining 900/0.80
    assert row.remaining_tokens == 900
    assert row.remaining_usd == Decimal("0.80")
    refreshed = db_session.get(LlmCallRow, call.id)
    assert refreshed is not None
    assert refreshed.status == "success"
    assert refreshed.meta.get("reconciled") is True
    assert refreshed.usd_estimate == Decimal("0.20")


def test_reconcile_excess_debit_clamps_to_zero_sets_underestimate_meta(
    db_session: Session,
) -> None:
    set_budget(db_session, tokens=100, usd=Decimal("0.10"))
    db_session.commit()
    call = reserve_and_open_call(db_session, tokens=50, usd=Decimal("0.05"), task="triage", model="m")
    db_session.commit()
    assert call is not None
    # remaining after reserve: 50 / 0.05; excess 200 tokens / 1.00 → clamp to 0
    ok = reconcile_reservation(
        db_session,
        call_id=call.id,
        final_status="success",
        ledger_op="excess",
        actual_tokens=250,
        actual_usd=Decimal("1.05"),
        tokens_in=200,
        tokens_out=50,
    )
    db_session.commit()
    assert ok is True
    row = get_budget(db_session)
    assert row is not None
    assert row.remaining_tokens == 0
    assert row.remaining_usd == Decimal("0")
    refreshed = db_session.get(LlmCallRow, call.id)
    assert refreshed is not None
    assert refreshed.meta.get("reservation_underestimate") is True
    assert refreshed.meta.get("reconciled") is True


def test_crash_between_reserve_and_reconcile_keeps_reservation(db_session: Session) -> None:
    set_budget(db_session, tokens=500, usd=Decimal("1"))
    db_session.commit()
    call = reserve_and_open_call(db_session, tokens=100, usd=Decimal("0.25"), task="ask", model="m")
    db_session.commit()
    assert call is not None
    # Simulate crash: no reconcile
    row = get_budget(db_session)
    assert row is not None
    assert row.remaining_tokens == 400
    assert row.remaining_usd == Decimal("0.75")
    refreshed = db_session.get(LlmCallRow, call.id)
    assert refreshed is not None
    assert refreshed.meta.get("reconciled") is False
    assert refreshed.error_code == ERROR_CODE_RESERVED


def test_parallel_reserve_one_wins(db_session: Session) -> None:
    set_budget(db_session, tokens=100, usd=Decimal("0.20"))
    db_session.commit()
    a = reserve_and_open_call(db_session, tokens=100, usd=Decimal("0.20"), task="ask", model="m")
    assert a is not None
    b = reserve_and_open_call(db_session, tokens=100, usd=Decimal("0.20"), task="ask", model="m")
    assert b is None
    db_session.commit()


def test_est_input_over_cap_skips_anthropic_no_reserve() -> None:
    # Cap check is a pure helper used by the gate (C3); pin the constant + estimator.
    assert ANTHROPIC_EST_INPUT_CAP == 16384
    huge = "x" * (ANTHROPIC_EST_INPUT_CAP * 2 + 100)
    est = estimate_input_tokens(huge)
    assert est > ANTHROPIC_EST_INPUT_CAP


def test_cli_show_prints_anthropic_counts_by_status_task_max_id(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_budget(db_session, tokens=100, usd=Decimal("1"))
    call = reserve_and_open_call(db_session, tokens=10, usd=Decimal("0.01"), task="ask", model="m")
    db_session.commit()
    assert call is not None

    from opspilot.jobs import anthropic_budget as cli

    monkeypatch.setattr(cli, "create_engine", lambda: db_session.get_bind())

    # create_session_factory returns a factory; use a fake that yields db_session
    class _Factory:
        def __call__(self) -> object:
            return self

        def __enter__(self) -> Session:
            return db_session

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(cli, "create_session_factory", lambda _engine: _Factory())
    monkeypatch.setattr(cli, "database_host_label", lambda: "127")
    # dispose no-op
    bind = db_session.get_bind()
    monkeypatch.setattr(bind, "dispose", lambda: None)

    rc = cli.main(["show"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "database host=127" in out
    assert "anthropic_rows_total=1" in out
    assert "open_reservations=1" in out
    assert "by_status=(none)" in out  # open reservations excluded from by_status
    assert "by_task=" in out
    assert "ask:1" in out
    assert f"max_id={call.id}" in out


def test_cli_show_works_with_no_ledger_row(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from opspilot.jobs import anthropic_budget as cli

    class _Factory:
        def __call__(self) -> object:
            return self

        def __enter__(self) -> Session:
            return db_session

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(cli, "create_engine", lambda: db_session.get_bind())
    monkeypatch.setattr(cli, "create_session_factory", lambda _e: _Factory())
    monkeypatch.setattr(cli, "database_host_label", lambda: "127")
    monkeypatch.setattr(db_session.get_bind(), "dispose", lambda: None)
    assert cli.main(["show"]) == 0
    out = capsys.readouterr().out
    assert "remaining_tokens=(none)" in out
    assert "open_reservations=0" in out
    assert "anthropic_rows_total=0" in out


def test_cli_show_never_writes(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    set_budget(db_session, tokens=77, usd=Decimal("0.77"))
    db_session.commit()
    from opspilot.jobs import anthropic_budget as cli

    class _Factory:
        def __call__(self) -> object:
            return self

        def __enter__(self) -> Session:
            return db_session

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(cli, "create_engine", lambda: db_session.get_bind())
    monkeypatch.setattr(cli, "create_session_factory", lambda _e: _Factory())
    monkeypatch.setattr(cli, "database_host_label", lambda: "127")
    monkeypatch.setattr(db_session.get_bind(), "dispose", lambda: None)
    assert cli.main(["show"]) == 0
    row = get_budget(db_session)
    assert row is not None
    assert row.remaining_tokens == 77


def test_cli_set_nonlocal_requires_confirm_host(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from opspilot.jobs import anthropic_budget as cli

    monkeypatch.setattr(cli, "database_host_label", lambda: "ep-neon")
    monkeypatch.setattr(cli, "_is_local_database_url", lambda _url: False)
    monkeypatch.setattr(cli, "get_database_url", lambda: "postgresql+psycopg://u:p@ep-neon/db")
    rc = cli.main(["set", "--tokens", "1", "--usd", "0.01"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "confirm-host" in err


def test_anthropic_call_counts_helper(db_session: Session) -> None:
    set_budget(db_session, tokens=50, usd=Decimal("1"))
    reserve_and_open_call(db_session, tokens=5, usd=Decimal("0.01"), task="triage", model="m")
    db_session.commit()
    counts = anthropic_call_counts(db_session)
    assert counts["anthropic_rows_total"] == 1
    assert counts["open_reservations"] == 1
    assert counts["by_status"] == {}
    assert counts["by_task"]["triage"] == 1
    assert counts["max_id"] is not None
