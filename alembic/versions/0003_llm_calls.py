"""Add llm_calls and llm_budget_counters tables.

Revision ID: 0003_llm_calls
Revises: 0002_runs_finished_at_idx
Create Date: 2026-09-29

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_llm_calls"
down_revision: str | None = "0002_runs_finished_at_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("task", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("ttft_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usd_estimate", sa.Numeric(12, 6), nullable=True),
        sa.Column("prompt_version", sa.CHAR(length=64), nullable=True),
        sa.Column("run_id", sa.String(length=128), nullable=True),
        sa.Column("work_item_id", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_llm_calls_created_at", "llm_calls", ["created_at"])
    op.create_index("ix_llm_calls_provider_status", "llm_calls", ["provider", "status"])
    op.create_index("ix_llm_calls_request_id", "llm_calls", ["request_id"])

    op.create_table(
        "llm_budget_counters",
        sa.Column("provider", sa.String(length=64), primary_key=True),
        sa.Column("day_utc", sa.Date(), primary_key=True),
        sa.Column("req_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tok_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("llm_budget_counters")
    op.drop_index("ix_llm_calls_request_id", table_name="llm_calls")
    op.drop_index("ix_llm_calls_provider_status", table_name="llm_calls")
    op.drop_index("ix_llm_calls_created_at", table_name="llm_calls")
    op.drop_table("llm_calls")
