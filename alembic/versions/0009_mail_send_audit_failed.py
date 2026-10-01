"""Ask HITL audit columns: send_failed + error_code (expand-only).

Revision ID: 0009_mail_send_audit_failed
Revises: 0008_ask_hitl_send
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_mail_send_audit_failed"
down_revision: str | None = "0008_ask_hitl_send"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mail_send_audit",
        sa.Column("send_failed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "mail_send_audit",
        sa.Column("error_code", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mail_send_audit", "error_code")
    op.drop_column("mail_send_audit", "send_failed")
