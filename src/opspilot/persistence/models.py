"""SQLAlchemy ORM models (Postgres)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
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


class OpsJobRow(Base):
    """Morning / sync-drain runner job (B6)."""

    __tablename__ = "ops_jobs"
    __table_args__ = (
        CheckConstraint("job_kind IN ('morning','sync_drain')", name="ck_ops_jobs_job_kind"),
        CheckConstraint(
            "status IN ('queued','running','succeeded','partial','failed','abandoned','noop')",
            name="ck_ops_jobs_status",
        ),
        Index(
            "uq_ops_jobs_morning_effective",
            "day_utc",
            unique=True,
            postgresql_where=text(
                "job_kind='morning' AND force_override=false AND status IN ('queued','running','succeeded','partial')"
            ),
        ),
        Index(
            "ix_ops_jobs_kind_created",
            "job_kind",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index(
            "ix_ops_jobs_active",
            "status",
            postgresql_where=text("status IN ('queued','running')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    day_utc: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    force_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triaged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rules_fallback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_ceiling: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gmail_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gmail_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calendar_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gmail_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    calendar_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ceiling_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    budget_exhausted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reauth_needed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    run_id: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("runs.run_id", ondelete="SET NULL"), nullable=True
    )
    telegram_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_generation: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class OpsJobLeaseRow(Base):
    """Singleton lease slot (pooler-safe job runner fence)."""

    __tablename__ = "ops_job_lease"
    __table_args__ = (CheckConstraint("slot = 1", name="ck_ops_job_lease_slot"),)

    slot: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    job_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("ops_jobs.id", ondelete="SET NULL"), nullable=True
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class TriageCorrectionRow(Base):
    """Operator triage overlay (does not mutate rules/prompts)."""

    __tablename__ = "triage_corrections"

    work_item_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("work_items.id", ondelete="CASCADE"), primary_key=True
    )
    urgency: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    sentiment: Mapped[str] = mapped_column(String(32), nullable=False)
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


class AnthropicPrepaidBudgetRow(Base):
    """Singleton prepaid ledger row (D-023); id must be 1."""

    __tablename__ = "anthropic_prepaid_budget"
    __table_args__ = (CheckConstraint("id = 1", name="ck_anthropic_prepaid_budget_id"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    remaining_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    remaining_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
