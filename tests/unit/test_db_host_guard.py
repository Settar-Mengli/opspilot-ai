"""Unit tests for hermetic DATABASE_URL host guard (D4)."""

from __future__ import annotations

import pytest
from tests.db_host_guard import assert_pytest_database_host_is_local, is_local_database_host


def test_is_local_database_host_accepts_loopback_and_ci_service() -> None:
    assert is_local_database_host("postgresql+psycopg://u:p@127.0.0.1:5432/opspilot")
    assert is_local_database_host("postgresql+psycopg://u:p@localhost:5432/opspilot_test")
    assert is_local_database_host("postgresql+psycopg://u:p@postgres:5432/opspilot")
    assert is_local_database_host("postgresql+psycopg://u:p@[::1]:5432/opspilot")


def test_is_local_database_host_rejects_remote_first_label() -> None:
    # Fictional remote-style host — must not be accepted.
    assert not is_local_database_host("postgresql+psycopg://u:p@ep-fixture-name.example.neon.tech/neondb")
    assert not is_local_database_host("postgresql+psycopg://u:p@db.example.com/opspilot")


def test_assert_pytest_database_host_is_local_raises_with_label_only() -> None:
    with pytest.raises(RuntimeError) as exc:
        assert_pytest_database_host_is_local("postgresql+psycopg://u:p@ep-fixture-name.example.neon.tech/neondb")
    msg = str(exc.value)
    assert "host=ep-fixture-name" in msg
    assert "neon.tech" not in msg
    assert assert_pytest_database_host_is_local("postgresql+psycopg://opspilot:opspilot@127.0.0.1:5432/opspilot") in {
        "127.0.0.1",
        "127",
    }
