"""Gmail readonly client (headers + text only; attachments ignored)."""

from __future__ import annotations

import base64
import email.utils
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from opspilot.integrations.google_http import GoogleHttpError, GoogleTransport

GMAIL_API = "https://gmail.googleapis.com/gmail/v1"


@dataclass(frozen=True)
class GmailMessage:
    provider_id: str
    thread_id: str | None
    subject: str
    sender: str
    body: str
    received_at: datetime


def _decode_b64(data: str) -> str:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad).decode("utf-8", errors="replace")


def _walk_parts(payload: dict[str, Any]) -> str:
    """Prefer text/plain; skip parts with filename (attachments)."""
    if payload.get("filename"):
        return ""
    mime = str(payload.get("mimeType") or "")
    body = payload.get("body") or {}
    data = body.get("data")
    if mime == "text/plain" and isinstance(data, str) and data:
        return _decode_b64(data)
    texts: list[str] = []
    for part in payload.get("parts") or []:
        if not isinstance(part, dict):
            continue
        texts.append(_walk_parts(part))
    return "\n".join(t for t in texts if t).strip()


def _header_map(payload: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for h in payload.get("headers") or []:
        if isinstance(h, dict) and h.get("name") and h.get("value") is not None:
            out[str(h["name"]).lower()] = str(h["value"])
    return out


def parse_message(raw: dict[str, Any]) -> GmailMessage:
    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
    headers = _header_map(payload if isinstance(payload, dict) else {})
    subject = headers.get("subject") or "(no subject)"
    sender = headers.get("from") or "unknown"
    date_hdr = headers.get("date")
    received = datetime.now(UTC)
    if date_hdr:
        try:
            parsed = email.utils.parsedate_to_datetime(date_hdr)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            received = parsed
        except (TypeError, ValueError, IndexError):
            pass
    body = _walk_parts(payload if isinstance(payload, dict) else {})
    body = re.sub(r"\s+", " ", body).strip()
    return GmailMessage(
        provider_id=str(raw.get("id") or ""),
        thread_id=str(raw.get("threadId") or "") or None,
        subject=subject,
        sender=sender,
        body=body,
        received_at=received,
    )


class GmailClient:
    def __init__(self, *, access_token: str, transport: GoogleTransport) -> None:
        self._token = access_token
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def profile_history_id(self) -> str:
        resp = self._transport.request("GET", f"{GMAIL_API}/users/me/profile", headers=self._headers())
        if resp.status_code >= 400:
            raise GoogleHttpError("gmail_profile_failed", status_code=resp.status_code)
        hid = str(resp.json().get("historyId") or "")
        if not hid:
            raise GoogleHttpError("gmail_missing_history_id")
        return hid

    def list_message_ids(self, *, max_results: int = 50) -> list[str]:
        resp = self._transport.request(
            "GET",
            f"{GMAIL_API}/users/me/messages",
            headers=self._headers(),
            params={"maxResults": max_results},
        )
        if resp.status_code >= 400:
            raise GoogleHttpError("gmail_list_failed", status_code=resp.status_code)
        msgs = resp.json().get("messages") or []
        return [str(m["id"]) for m in msgs if isinstance(m, dict) and m.get("id")]

    def get_message(self, message_id: str) -> GmailMessage:
        resp = self._transport.request(
            "GET",
            f"{GMAIL_API}/users/me/messages/{message_id}",
            headers=self._headers(),
            params={"format": "full"},
        )
        if resp.status_code >= 400:
            raise GoogleHttpError("gmail_get_failed", status_code=resp.status_code)
        return parse_message(resp.json())

    def history_message_ids(self, *, start_history_id: str) -> list[str] | None:
        """Return new message ids, or None if history expired (caller should full sync)."""
        resp = self._transport.request(
            "GET",
            f"{GMAIL_API}/users/me/history",
            headers=self._headers(),
            params={"startHistoryId": start_history_id, "historyTypes": "messageAdded"},
        )
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise GoogleHttpError("gmail_history_failed", status_code=resp.status_code)
        ids: list[str] = []
        for entry in resp.json().get("history") or []:
            if not isinstance(entry, dict):
                continue
            for added in entry.get("messagesAdded") or []:
                if isinstance(added, dict):
                    msg = added.get("message") or {}
                    if isinstance(msg, dict) and msg.get("id"):
                        ids.append(str(msg["id"]))
        return ids

    def send_reply(
        self,
        *,
        thread_id: str,
        in_reply_to_provider_id: str,
        to_addrs: str,
        subject: str,
        body: str,
    ) -> str:
        """Reply in-thread. Belt-and-suspenders DEMO_MODE + allowlist before HTTP."""
        from opspilot.services.operator_session import demo_mode_enabled
        from opspilot.services.send_allowlist import recipients_allowed

        if demo_mode_enabled():
            raise GoogleHttpError("demo_mode_blocks_send")
        if not recipients_allowed(to_addrs):
            raise GoogleHttpError("recipient_not_allowlisted")
        if not thread_id or not in_reply_to_provider_id:
            raise GoogleHttpError("missing_thread_or_provider")

        import email.message

        msg = email.message.EmailMessage()
        msg["To"] = to_addrs
        msg["Subject"] = subject
        msg["In-Reply-To"] = in_reply_to_provider_id
        msg["References"] = in_reply_to_provider_id
        msg.set_content(body)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii").rstrip("=")
        resp = self._transport.request(
            "POST",
            f"{GMAIL_API}/users/me/messages/send",
            headers=self._headers(),
            json={"raw": raw, "threadId": thread_id},
        )
        if resp.status_code >= 400:
            raise GoogleHttpError("gmail_send_failed", status_code=resp.status_code)
        mid = str(resp.json().get("id") or "")
        if not mid:
            raise GoogleHttpError("gmail_send_missing_id")
        return mid
