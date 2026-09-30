"""Add nullable confidence + evidence_refs on triage_decisions (P12).

Revision ID: 0006_triage_confidence_evidence
Revises: 0005_run_artifacts_name_idx
Create Date: 2026-09-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_triage_confidence_evidence"
down_revision: str | None = "0005_run_artifacts_name_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("triage_decisions", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column(
        "triage_decisions",
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("triage_decisions", "evidence_refs")
    op.drop_column("triage_decisions", "confidence")
