"""SQLAlchemy ORM models (Postgres)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CHAR, BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class WorkItemRow(Base):
    __tablename__ = "work_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_or_title: Mapped[str] = mapped_column(Text, nullable=False)
    body_or_description: Mapped[str] = mapped_column(Text, nullable=False)
    sender_or_requester: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    triage_decisions: Mapped[list[TriageDecisionRow]] = relationship(back_populates="work_item")


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
    __table_args__ = (UniqueConstraint("run_id", "name", name="uq_run_artifacts_run_name"),)

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
