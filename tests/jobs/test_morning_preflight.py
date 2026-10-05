"""Preflight tests: Alembic head mismatch prevents any DB write."""

from __future__ import annotations

import pytest

from opspilot.jobs.morning_run import PreflightError, _preflight


def test_head_mismatch_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the DB Alembic head differs from expected, preflight raises."""
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "0")
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.delenv("LLM_DISABLE", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://opspilot:opspilot@127.0.0.1:5432/opspilot")

    # Stub Alembic to return a different head.
    import opspilot.jobs.morning_run as mod

    class _FakeScript:
        def get_current_head(self) -> str:
            return "0010_ops_jobs_corrections_budget"

    class _FakeConfig:
        def __init__(self, *a: object, **kw: object) -> None:
            pass

    # Make DB return a wrong head.
    _original_preflight = mod._preflight

    def _patched_preflight() -> None:
        # Patch at the Alembic + DB level.

        class _FakeResult:
            def scalar(self) -> str:
                return "0009_wrong_head"

        class _FakeSession:
            def execute(self, *a: object, **kw: object) -> _FakeResult:
                return _FakeResult()

            def __enter__(self) -> _FakeSession:
                return self

            def __exit__(self, *a: object) -> None:
                pass

        class _FakeFactory:
            def __call__(self) -> _FakeSession:
                return _FakeSession()

        class _FakeEngine:
            def dispose(self) -> None:
                pass

        monkeypatch.setattr(mod, "_EXPECTED_ALEMBIC_HEAD", "0010_ops_jobs_corrections_budget")
        monkeypatch.setattr("opspilot.persistence.db.create_engine", lambda *a, **kw: _FakeEngine())
        monkeypatch.setattr("opspilot.persistence.db.create_session_factory", lambda *a, **kw: _FakeFactory())

        # Also stub Alembic config/script.
        monkeypatch.setattr("alembic.config.Config", _FakeConfig)
        monkeypatch.setattr(
            "alembic.script.ScriptDirectory.from_config",
            staticmethod(lambda *a, **kw: _FakeScript()),
        )
        _original_preflight()

    with pytest.raises(PreflightError, match="alembic_head_mismatch"):
        _patched_preflight()


def test_anthropic_enabled_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Preflight rejects when Anthropic is enabled."""
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x:x@127.0.0.1:5432/x")
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.delenv("LLM_DISABLE", raising=False)
    with pytest.raises(PreflightError, match="anthropic_enabled"):
        _preflight()


def test_force_rules_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Preflight rejects when FORCE_RULES is set."""
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "0")
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x:x@127.0.0.1:5432/x")
    with pytest.raises(PreflightError, match="env_block"):
        _preflight()
