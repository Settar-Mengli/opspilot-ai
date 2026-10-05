"""B6: ops_jobs, lease, triage corrections, anthropic prepaid budget (expand-only).

Revision ID: 0010_ops_jobs_corrections_budget
Revises: 0009_mail_send_audit_failed
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_ops_jobs_corrections_budget"
down_revision: str | None = "0009_mail_send_audit_failed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ops_jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_kind", sa.String(length=32), nullable=False),
        sa.Column("day_utc", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("force_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triaged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rules_fallback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_ceiling", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gmail_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gmail_removed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calendar_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gmail_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("calendar_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ceiling_hit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("budget_exhausted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reauth_needed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("run_id", sa.String(length=128), nullable=True),
        sa.Column("telegram_error_code", sa.String(length=64), nullable=True),
        sa.Column("lease_generation", sa.BigInteger(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.CheckConstraint("job_kind IN ('morning','sync_drain')", name="ck_ops_jobs_job_kind"),
        sa.CheckConstraint(
            "status IN ('queued','running','succeeded','partial','failed','abandoned','noop')",
            name="ck_ops_jobs_status",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_ops_jobs_morning_effective",
        "ops_jobs",
        ["day_utc"],
        unique=True,
        postgresql_where=sa.text(
            "job_kind='morning' AND force_override=false AND status IN ('queued','running','succeeded','partial')"
        ),
    )
    op.create_index(
        "ix_ops_jobs_kind_created",
        "ops_jobs",
        ["job_kind", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index(
        "ix_ops_jobs_active",
        "ops_jobs",
        ["status"],
        postgresql_where=sa.text("status IN ('queued','running')"),
    )

    op.create_table(
        "ops_job_lease",
        sa.Column("slot", sa.SmallInteger(), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generation", sa.BigInteger(), nullable=False, server_default="0"),
        sa.CheckConstraint("slot = 1", name="ck_ops_job_lease_slot"),
        sa.ForeignKeyConstraint(["job_id"], ["ops_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("slot"),
    )
    op.execute(sa.text("INSERT INTO ops_job_lease (slot, job_id, heartbeat_at, generation) VALUES (1, NULL, NULL, 0)"))

    op.create_table(
        "triage_corrections",
        sa.Column("work_item_id", sa.String(length=64), nullable=False),
        sa.Column("urgency", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("sentiment", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("work_item_id"),
    )

    op.create_table(
        "anthropic_prepaid_budget",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("remaining_tokens", sa.BigInteger(), nullable=False),
        sa.Column("remaining_usd", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_anthropic_prepaid_budget_id"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("anthropic_prepaid_budget")
    op.drop_table("triage_corrections")
    op.drop_table("ops_job_lease")
    op.drop_index("ix_ops_jobs_active", table_name="ops_jobs")
    op.drop_index("ix_ops_jobs_kind_created", table_name="ops_jobs")
    op.drop_index("uq_ops_jobs_morning_effective", table_name="ops_jobs")
    op.drop_table("ops_jobs")
