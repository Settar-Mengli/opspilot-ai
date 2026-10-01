"""Mail draft edit + approve routes (D-033)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from opspilot.api.deps import get_db_session
from opspilot.api.schemas import safe_error
from opspilot.services.mail_hitl import MailHitlError, approve_and_send, edit_draft
from opspilot.services.operator_session import COOKIE_NAME, verify_session

router = APIRouter(tags=["mail"])


class DraftEditRequest(BaseModel):
    model_config = {"extra": "forbid"}

    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=8000)


class DraftApproveRequest(BaseModel):
    payload_sha256: str = Field(..., min_length=64, max_length=64)
    idempotency_key: str | None = Field(default=None, max_length=128)


def _require_operator(request: Request) -> str:
    sess = verify_session(request.cookies.get(COOKIE_NAME))
    if sess is None:
        raise safe_error(401, "operator_auth_required", "Operator session required.")
    return sess.email


def _request_id(http_request: Request) -> str | None:
    rid = getattr(http_request.state, "request_id", None)
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    return None


@router.post("/mail/drafts/{draft_id}/edit")
def mail_draft_edit(
    draft_id: str,
    payload: DraftEditRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    _require_operator(request)
    # Reject if client smuggled forbidden fields via model_extra (extra=forbid by default in pydantic v2)
    try:
        return edit_draft(session, draft_id, payload.model_dump())
    except MailHitlError as exc:
        status = 404 if exc.code == "draft_not_found" else 400
        raise safe_error(status, exc.code, exc.message) from exc


@router.post("/mail/drafts/{draft_id}/approve")
def mail_draft_approve(
    draft_id: str,
    payload: DraftApproveRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    email = _require_operator(request)
    try:
        return approve_and_send(
            session,
            draft_id,
            expected_payload_sha256=payload.payload_sha256,
            operator_email=email,
            request_id=_request_id(request),
            idempotency_key=payload.idempotency_key,
        )
    except MailHitlError as exc:
        if exc.code == "demo_mode_blocks_send":
            raise safe_error(403, exc.code, exc.message) from exc
        if exc.code == "recipient_not_allowlisted":
            raise safe_error(403, exc.code, exc.message) from exc
        status = 404 if exc.code == "draft_not_found" else 400
        raise safe_error(status, exc.code, exc.message) from exc
