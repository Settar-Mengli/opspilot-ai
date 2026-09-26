"""Initial work_items, runs, run_artifacts, triage_decisions.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-26

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("subject_or_title", sa.Text(), nullable=False),
        sa.Column("body_or_description", sa.Text(), nullable=False),
        sa.Column("sender_or_requester", sa.Text(), nullable=False),
        sa.Column("received_at", sa.String(length=64), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.String(length=64), nullable=True),
        sa.Column("finished_at", sa.String(length=64), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_file", sa.Text(), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=True),
        sa.Column("triage_count", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_table(
        "run_artifacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "name", name="uq_run_artifacts_run_name"),
    )
    op.create_table(
        "triage_decisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_item_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=True),
        sa.Column("urgency", sa.String(length=32), nullable=False),
        sa.Column("urgency_reason", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("category_reason", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.String(length=32), nullable=False),
        sa.Column("sentiment_reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_item_id", "run_id", name="uq_triage_work_item_run"),
    )


def downgrade() -> None:
    op.drop_table("triage_decisions")
    op.drop_table("run_artifacts")
    op.drop_table("runs")
    op.drop_table("work_items")
