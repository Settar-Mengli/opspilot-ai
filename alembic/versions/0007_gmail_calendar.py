"""Gmail/Calendar: provider_id, oauth credentials, sync cursors, meetings.

Revision ID: 0007_gmail_calendar
Revises: 0006_triage_confidence_evidence
Create Date: 2026-09-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_gmail_calendar"
down_revision: str | None = "0006_triage_confidence_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("work_items", sa.Column("provider_id", sa.String(length=128), nullable=True))
    op.add_column("work_items", sa.Column("thread_id", sa.String(length=128), nullable=True))
    op.create_unique_constraint("uq_work_items_provider_id", "work_items", ["provider_id"])

    op.create_table(
        "oauth_credentials",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("account_email", sa.Text(), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("refresh_token_enc", postgresql.BYTEA(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "account_email", name="uq_oauth_credentials_provider_email"),
    )

    op.create_table(
        "sync_cursors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("account_email", sa.Text(), nullable=False),
        sa.Column("cursor_kind", sa.String(length=64), nullable=False),
        sa.Column("cursor_value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "account_email",
            "cursor_kind",
            name="uq_sync_cursors_provider_email_kind",
        ),
    )

    op.create_table(
        "meetings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", name="uq_meetings_provider_id"),
    )


def downgrade() -> None:
    op.drop_table("meetings")
    op.drop_table("sync_cursors")
    op.drop_table("oauth_credentials")
    op.drop_constraint("uq_work_items_provider_id", "work_items", type_="unique")
    op.drop_column("work_items", "thread_id")
    op.drop_column("work_items", "provider_id")
