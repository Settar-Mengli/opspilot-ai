"""SQLAlchemy ORM models (Postgres)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class WorkItemRow(Base):
    __tablename__ = "work_items"
    __table_args__ = (UniqueConstraint("provider_id", name="uq_work_items_provider_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_or_title: Mapped[str] = mapped_column(Text, nullable=False)
    body_or_description: Mapped[str] = mapped_column(Text, nullable=False)
    sender_or_requester: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    provider_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    triage_decisions: Mapped[list[TriageDecisionRow]] = relationship(
        back_populates="work_item",
        passive_deletes=True,
    )


class RunRow(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    input_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    triage_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    artifacts: Mapped[list[RunArtifactRow]] = relationship(back_populates="run", cascade="all, delete-orphan")
    triage_decisions: Mapped[list[TriageDecisionRow]] = relationship(back_populates="run")


class RunArtifactRow(Base):
    __tablename__ = "run_artifacts"
    __table_args__ = (
        UniqueConstraint("run_id", "name", name="uq_run_artifacts_run_name"),
        Index("ix_run_artifacts_name", "name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(128), ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)  # json | text
    content: Mapped[str] = mapped_column(Text, nullable=False)

    run: Mapped[RunRow] = relationship(back_populates="artifacts")


class TriageDecisionRow(Base):
    __tablename__ = "triage_decisions"
    __table_args__ = (UniqueConstraint("work_item_id", "run_id", name="uq_triage_work_item_run"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_item_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("work_items.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("runs.run_id", ondelete="SET NULL"), nullable=True
    )
    urgency: Mapped[str] = mapped_column(String(32), nullable=False)
    urgency_reason: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    category_reason: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[str] = mapped_column(String(32), nullable=False)
    sentiment_reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_refs: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)

    work_item: Mapped[WorkItemRow] = relationship(back_populates="triage_decisions")
    run: Mapped[RunRow | None] = relationship(back_populates="triage_decisions")


class LlmCallRow(Base):
    """One row per provider attempt (D-019)."""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ttft_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usd_estimate: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    run_id: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("runs.run_id", ondelete="SET NULL"), nullable=True
    )
    work_item_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("work_items.id", ondelete="SET NULL"), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class LlmBudgetCounterRow(Base):
    """UTC-day request/token counters per provider."""

    __tablename__ = "llm_budget_counters"

    provider: Mapped[str] = mapped_column(String(64), primary_key=True)
    day_utc: Mapped[date] = mapped_column(Date, primary_key=True)
    req_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tok_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class OAuthCredentialRow(Base):
    """Encrypted OAuth refresh token at rest (D-016 / D-027 bytea)."""

    __tablename__ = "oauth_credentials"
    __table_args__ = (UniqueConstraint("provider", "account_email", name="uq_oauth_credentials_provider_email"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    account_email: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class SyncCursorRow(Base):
    """Provider sync checkpoints (X1): Gmail historyId / Calendar syncToken."""

    __tablename__ = "sync_cursors"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "account_email",
            "cursor_kind",
            name="uq_sync_cursors_provider_email_kind",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    account_email: Mapped[str] = mapped_column(Text, nullable=False)
    cursor_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    cursor_value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class MeetingRow(Base):
    """Minimal calendar meeting for WeekPanel (B4)."""

    __tablename__ = "meetings"
    __table_args__ = (UniqueConstraint("provider_id", name="uq_meetings_provider_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class MailDraftRow(Base):
    """HITL reply draft (D-033). Recipients/thread ids are server-owned."""

    __tablename__ = "mail_drafts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    work_item_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("work_items.id", ondelete="SET NULL"), nullable=True
    )
    thread_id: Mapped[str] = mapped_column(String(128), nullable=False)
    gmail_provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    to_addrs: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    operator_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class MailSendAuditRow(Base):
    """Immutable send attempt audit (D-027: no CASCADE erase)."""

    __tablename__ = "mail_send_audit"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_mail_send_audit_idempotency_key"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    draft_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("mail_drafts.id", ondelete="SET NULL"), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    to_addrs: Mapped[str] = mapped_column(Text, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    gmail_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operator_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    demo_mode_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allowlist_denied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    send_failed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
