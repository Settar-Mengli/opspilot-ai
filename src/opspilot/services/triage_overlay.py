"""Triage overlay: newest decision ⊕ correction labels (B6 C6).

Returns the effective triage label for each work item:
- Labels come from the correction row when one exists, else from the
  newest TriageDecisionRow.
- Reason strings always come from the original decision (corrections
  override *labels* only — urgency / category / sentiment).
- Each record includes ``corrected: bool`` so the API consumer can
  distinguish human-corrected items.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from opspilot.persistence.models import TriageCorrectionRow, TriageDecisionRow, WorkItemRow


def latest_triage_with_overlay(
    session: Session,
    *,
    gmail_only: bool = False,
) -> list[dict[str, Any]]:
    """Latest triage decision per work_item_id with correction overlay.

    When *gmail_only* is True, only ``source_type=gmail`` work items are
    returned (same filter used by connected-Gmail routes).
    """
    stmt = (
        select(TriageDecisionRow, WorkItemRow)
        .join(WorkItemRow, TriageDecisionRow.work_item_id == WorkItemRow.id)
        .order_by(desc(TriageDecisionRow.id))
    )
    if gmail_only:
        stmt = stmt.where(WorkItemRow.source_type == "gmail")

    rows = session.execute(stmt).all()

    # Deduplicate: keep only the newest decision per work_item_id.
    seen: set[str] = set()
    decisions: list[tuple[TriageDecisionRow, WorkItemRow]] = []
    for decision, work_item in rows:
        if decision.work_item_id in seen:
            continue
        seen.add(decision.work_item_id)
        decisions.append((decision, work_item))

    # Batch-load corrections for all work_item_ids.
    wids = [d.work_item_id for d, _ in decisions]
    corrections: dict[str, TriageCorrectionRow] = {}
    if wids:
        corr_rows = session.scalars(select(TriageCorrectionRow).where(TriageCorrectionRow.work_item_id.in_(wids))).all()
        corrections = {c.work_item_id: c for c in corr_rows}

    payload: list[dict[str, Any]] = []
    for decision, work_item in decisions:
        corr = corrections.get(decision.work_item_id)
        payload.append(
            {
                "id": decision.work_item_id,
                "subject_or_title": work_item.subject_or_title,
                "urgency": corr.urgency if corr else decision.urgency,
                "urgency_reason": decision.urgency_reason,
                "category": corr.category if corr else decision.category,
                "category_reason": decision.category_reason,
                "sentiment": corr.sentiment if corr else decision.sentiment,
                "sentiment_reason": decision.sentiment_reason,
                "corrected": corr is not None,
            }
        )
    return payload


def promotion_hook(session: Session) -> list[dict[str, Any]]:
    """Export corrections as training-ready dataset rows (D-028 prep).

    Returns one dict per correction row, each containing the corrected
    labels alongside the original decision reasons and work-item text.
    """
    stmt = (
        select(TriageCorrectionRow, TriageDecisionRow, WorkItemRow)
        .join(WorkItemRow, TriageCorrectionRow.work_item_id == WorkItemRow.id)
        .outerjoin(
            TriageDecisionRow,
            TriageCorrectionRow.work_item_id == TriageDecisionRow.work_item_id,
        )
        .order_by(TriageCorrectionRow.work_item_id, desc(TriageDecisionRow.id))
    )
    rows = session.execute(stmt).all()

    seen: set[str] = set()
    dataset: list[dict[str, Any]] = []
    for corr, decision, work_item in rows:
        if corr.work_item_id in seen:
            continue
        seen.add(corr.work_item_id)
        entry: dict[str, Any] = {
            "work_item_id": corr.work_item_id,
            "subject_or_title": work_item.subject_or_title,
            "body_or_description": work_item.body_or_description,
            "corrected_urgency": corr.urgency,
            "corrected_category": corr.category,
            "corrected_sentiment": corr.sentiment,
        }
        if decision is not None:
            entry["original_urgency"] = decision.urgency
            entry["original_category"] = decision.category
            entry["original_sentiment"] = decision.sentiment
        dataset.append(entry)
    return dataset
