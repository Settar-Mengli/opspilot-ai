"""Expand/contract String timestamps → timestamptz (D-027 / G-01).

Revision ID: 0004_timestamptz
Revises: 0003_llm_calls
Create Date: 2026-09-29

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_timestamptz"
down_revision: str | None = "0003_llm_calls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Expand
    op.add_column("runs", sa.Column("started_at_ts", sa.DateTime(timezone=True), nullable=True))
    op.add_column("runs", sa.Column("finished_at_ts", sa.DateTime(timezone=True), nullable=True))
    op.add_column("work_items", sa.Column("received_at_ts", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        """
        UPDATE runs
        SET started_at_ts = CASE
            WHEN started_at IS NULL OR btrim(started_at) = '' THEN NULL
            ELSE started_at::timestamptz
        END
        """
    )
    op.execute(
        """
        UPDATE runs
        SET finished_at_ts = CASE
            WHEN finished_at IS NULL OR btrim(finished_at) = '' THEN NULL
            ELSE finished_at::timestamptz
        END
        """
    )
    op.execute(
        """
        UPDATE work_items
        SET received_at_ts = CASE
            WHEN received_at IS NULL OR btrim(received_at) = '' THEN NULL
            ELSE received_at::timestamptz
        END
        """
    )

    # Contract: drop string cols, rename ts cols
    op.drop_index("ix_runs_finished_at", table_name="runs")
    op.drop_column("runs", "started_at")
    op.drop_column("runs", "finished_at")
    op.alter_column("runs", "started_at_ts", new_column_name="started_at")
    op.alter_column("runs", "finished_at_ts", new_column_name="finished_at")
    op.create_index("ix_runs_finished_at", "runs", ["finished_at"])

    op.drop_column("work_items", "received_at")
    op.alter_column("work_items", "received_at_ts", new_column_name="received_at")
    op.execute(
        """
        UPDATE work_items
        SET received_at = TIMESTAMPTZ '1970-01-01 00:00:00+00'
        WHERE received_at IS NULL
        """
    )
    op.alter_column("work_items", "received_at", nullable=False)


def downgrade() -> None:
    op.add_column("work_items", sa.Column("received_at_str", sa.String(length=64), nullable=True))
    op.execute(
        """
        UPDATE work_items
        SET received_at_str = to_char(received_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
        """
    )
    op.drop_column("work_items", "received_at")
    op.alter_column("work_items", "received_at_str", new_column_name="received_at")
    op.alter_column("work_items", "received_at", nullable=False)

    op.drop_index("ix_runs_finished_at", table_name="runs")
    op.add_column("runs", sa.Column("started_at_str", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("finished_at_str", sa.String(length=64), nullable=True))
    op.execute(
        """
        UPDATE runs
        SET started_at_str = CASE
            WHEN started_at IS NULL THEN NULL
            ELSE to_char(started_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
        END,
        finished_at_str = CASE
            WHEN finished_at IS NULL THEN NULL
            ELSE to_char(finished_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
        END
        """
    )
    op.drop_column("runs", "started_at")
    op.drop_column("runs", "finished_at")
    op.alter_column("runs", "started_at_str", new_column_name="started_at")
    op.alter_column("runs", "finished_at_str", new_column_name="finished_at")
    op.create_index("ix_runs_finished_at", "runs", ["finished_at"])
