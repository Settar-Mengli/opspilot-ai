"""Add index on run_artifacts.name for name-only hot reads (DM-03).

Revision ID: 0005_run_artifacts_name_idx
Revises: 0004_timestamptz
Create Date: 2026-09-30

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_run_artifacts_name_idx"
down_revision: str | None = "0004_timestamptz"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_run_artifacts_name", "run_artifacts", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_run_artifacts_name", table_name="run_artifacts")
