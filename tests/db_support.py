"""DB helpers shared by persistence tests (not pytest fixtures)."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def alembic_upgrade(database_url: str) -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    os.environ["DATABASE_URL"] = database_url
    command.upgrade(cfg, "head")


def alembic_downgrade(database_url: str) -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    os.environ["DATABASE_URL"] = database_url
    command.downgrade(cfg, "base")
