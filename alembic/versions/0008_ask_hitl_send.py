"""Ask HITL: mail_drafts + mail_send_audit (expand-only).

Revision ID: 0008_ask_hitl_send
Revises: 0007_gmail_calendar
Create Date: 2026-10-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_ask_hitl_send"
down_revision: str | None = "0007_gmail_calendar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mail_drafts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("work_item_id", sa.String(length=64), nullable=True),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("gmail_provider_id", sa.String(length=128), nullable=False),
        sa.Column("to_addrs", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("operator_email", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mail_drafts_status", "mail_drafts", ["status"])

    op.create_table(
        "mail_send_audit",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("draft_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("to_addrs", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("gmail_message_id", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("operator_email", sa.Text(), nullable=True),
        sa.Column("demo_mode_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allowlist_denied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["mail_drafts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_mail_send_audit_idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("mail_send_audit")
    op.drop_index("ix_mail_drafts_status", table_name="mail_drafts")
    op.drop_table("mail_drafts")
