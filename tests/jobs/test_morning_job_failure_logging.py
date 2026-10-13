"""morning_run._log_job_failure: local detail vs GITHUB_ACTIONS codes-only (dual-branch pins)."""

from __future__ import annotations

import pytest

from opspilot.jobs import morning_run


def test_log_job_failure_local_uses_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    exception_calls: list[tuple[str, tuple[object, ...]]] = []
    error_calls: list[object] = []

    def _exception(msg: str, *args: object, **_kwargs: object) -> None:
        exception_calls.append((msg, args))

    def _error(*_a: object, **_k: object) -> None:
        error_calls.append(True)

    monkeypatch.setattr(morning_run.logger, "exception", _exception)
    monkeypatch.setattr(morning_run.logger, "error", _error)
    morning_run._log_job_failure(
        "morning_run failed job_id=%s",
        "job-1",
        exc=RuntimeError("secret-failure-detail"),
    )
    assert error_calls == []
    assert exception_calls == [("morning_run failed job_id=%s", ("job-1",))]


def test_log_job_failure_gha_type_and_code_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("CI", "true")
    recorded: list[str] = []
    exception_calls: list[object] = []

    def _error(msg: str, *args: object, **_kwargs: object) -> None:
        recorded.append(msg % args if args else msg)

    def _exception(*_a: object, **_k: object) -> None:
        exception_calls.append(True)

    monkeypatch.setattr(morning_run.logger, "error", _error)
    monkeypatch.setattr(morning_run.logger, "exception", _exception)
    morning_run._log_job_failure(
        "morning_run failed job_id=%s",
        "job-1",
        exc=RuntimeError("secret-failure-detail"),
    )
    assert exception_calls == []
    assert recorded
    joined = "\n".join(recorded)
    assert "error_code=RuntimeError" in joined
    assert "morning_run failed job_id=job-1" in joined
    assert "secret-failure-detail" not in joined
