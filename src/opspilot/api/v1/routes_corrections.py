"""Triage correction routes — POST/DELETE /api/v1/corrections/{work_item_id} (B6 C6)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from opspilot.api.csrf import require_csrf_origin
from opspilot.api.deps import get_db_session
from opspilot.api.schemas import safe_error
from opspilot.persistence.models import WorkItemRow
from opspilot.persistence.repositories import triage_corrections
from opspilot.services.operator_session import COOKIE_NAME, demo_mode_enabled, verify_session

router = APIRouter(tags=["corrections"])


class CorrectionRequest(BaseModel):
    model_config = {"extra": "forbid"}

    urgency: str = Field(..., min_length=1, max_length=32)
    category: str = Field(..., min_length=1, max_length=32)
    sentiment: str = Field(..., min_length=1, max_length=32)


def _require_operator(request: Request) -> str:
    sess = verify_session(request.cookies.get(COOKIE_NAME))
    if sess is None:
        raise safe_error(401, "operator_auth_required", "Operator session required.")
    return sess.email


@router.post("/corrections/{work_item_id}")
def upsert_correction(
    work_item_id: str,
    payload: CorrectionRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    require_csrf_origin(request)
    _require_operator(request)
    if demo_mode_enabled():
        raise safe_error(403, "demo_mode", "Corrections are disabled in demo mode.")
    if session.get(WorkItemRow, work_item_id) is None:
        raise safe_error(404, "work_item_not_found", "Work item not found.")
    row = triage_corrections.upsert_correction(
        session,
        work_item_id=work_item_id,
        urgency=payload.urgency,
        category=payload.category,
        sentiment=payload.sentiment,
    )
    return {
        "work_item_id": row.work_item_id,
        "urgency": row.urgency,
        "category": row.category,
        "sentiment": row.sentiment,
        "corrected": True,
    }


@router.delete("/corrections/{work_item_id}")
def delete_correction(
    work_item_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    require_csrf_origin(request)
    _require_operator(request)
    if demo_mode_enabled():
        raise safe_error(403, "demo_mode", "Corrections are disabled in demo mode.")
    deleted = triage_corrections.delete_correction(session, work_item_id)
    if not deleted:
        raise safe_error(404, "correction_not_found", "No correction exists for this work item.")
    return {"deleted": True, "work_item_id": work_item_id}
