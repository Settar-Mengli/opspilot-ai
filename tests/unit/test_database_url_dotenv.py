"""DATABASE_URL resolution, dotenv load, and host-label redaction."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from opspilot.persistence.db import (
    DEFAULT_DATABASE_URL,
    database_host_label,
    get_database_url,
    log_active_database_host,
)


def test_database_host_label_ipv4() -> None:
    assert database_host_label("postgresql+psycopg://u:s3cret@127.0.0.1:5432/opspilot") == "127"


def test_database_host_label_neon_style() -> None:
    url = "postgresql+psycopg://u:s3cret@ep-cool-name.us-east-2.aws.neon.tech/neondb?sslmode=require"
    assert database_host_label(url) == "ep-cool-name"


def test_database_host_label_never_leaks_secret() -> None:
    url = "postgresql+psycopg://op_user:super-secret-pass@db.example.com:5432/app"
    label = database_host_label(url)
    assert label == "db"
    assert "super-secret-pass" not in label
    assert "op_user" not in label
    assert "example.com" not in label
    assert "postgresql" not in label


def test_get_database_url_respects_existing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@ci-host:5432/ci")
    assert get_database_url() == "postgresql+psycopg://u:p@ci-host:5432/ci"
    assert database_host_label() == "ci-host"


def test_get_database_url_fallback_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("opspilot.persistence.db.load_repo_dotenv", lambda: False)
    assert get_database_url() == DEFAULT_DATABASE_URL


def test_get_database_url_uses_dotenv_when_unset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql+psycopg://u:p@ep-from-dotenv.example.neon.tech/db\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)

    def _load() -> bool:
        return bool(__import__("dotenv").load_dotenv(env_file))

    monkeypatch.setattr("opspilot.persistence.db.load_repo_dotenv", _load)
    assert "ep-from-dotenv" in get_database_url()
    label = log_active_database_host()
    assert label == "ep-from-dotenv"
    # Redacted label only — never a URL fragment.
    assert "postgresql" not in label
    assert ":p@" not in label


def test_load_dotenv_does_not_override_existing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql+psycopg://u:p@from-file:5432/db\n", encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@from-shell:5432/db")
    from dotenv import load_dotenv

    assert load_dotenv(env_file, override=False) is True
    assert os.environ["DATABASE_URL"].endswith("@from-shell:5432/db")


def test_db_host_cli_prints_label(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@ep-cli-check.us-east-1.aws.neon.tech/db")
    from opspilot.jobs.db_host import main

    assert main() == 0
    out = capsys.readouterr().out.strip()
    assert out == "database host=ep-cli-check"
    assert "postgresql" not in out
    assert ":p@" not in out
