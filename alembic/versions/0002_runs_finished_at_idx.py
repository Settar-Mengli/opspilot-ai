"""Add index on runs.finished_at for list_runs ordering.

Revision ID: 0002_runs_finished_at_idx
Revises: 0001_initial
Create Date: 2026-09-26

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_runs_finished_at_idx"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_runs_finished_at", "runs", ["finished_at"])


def downgrade() -> None:
    op.drop_index("ix_runs_finished_at", table_name="runs")
