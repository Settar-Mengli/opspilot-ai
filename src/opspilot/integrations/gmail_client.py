"""Gmail readonly client (headers + text only; attachments ignored)."""

from __future__ import annotations

import base64
import email.utils
import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from opspilot.integrations.google_http import GoogleHttpError, GoogleTransport, request_with_backoff

GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
_logger = logging.getLogger("opspilot.sync.gmail")


def _max_pages(env_name: str, default: int = 20) -> int:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


@dataclass(frozen=True)
class GmailMessage:
    provider_id: str
    thread_id: str | None
    subject: str
    sender: str
    body: str
    received_at: datetime
    label_ids: tuple[str, ...] = ()


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
    labels = tuple(str(x) for x in (raw.get("labelIds") or []) if x)
    return GmailMessage(
        provider_id=str(raw.get("id") or ""),
        thread_id=str(raw.get("threadId") or "") or None,
        subject=subject,
        sender=sender,
        body=body,
        received_at=received,
        label_ids=labels,
    )


class GmailClient:
    def __init__(self, *, access_token: str, transport: GoogleTransport) -> None:
        self._token = access_token
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def profile_history_id(self) -> str:
        resp = request_with_backoff(self._transport, "GET", f"{GMAIL_API}/users/me/profile", headers=self._headers())
        if resp.status_code >= 400:
            raise GoogleHttpError("gmail_profile_failed", status_code=resp.status_code)
        hid = str(resp.json().get("historyId") or "")
        if not hid:
            raise GoogleHttpError("gmail_missing_history_id")
        return hid

    def list_message_ids(self, *, max_results: int = 50, query: str | None = None) -> tuple[list[str], bool]:
        """Return (ids, truncated). Paginate until done or max pages."""
        ids: list[str] = []
        page_token: str | None = None
        max_pages = _max_pages("OPSPILOT_GMAIL_LIST_MAX_PAGES")
        truncated = False
        for page_i in range(max_pages):
            params: dict[str, Any] = {"maxResults": max_results}
            if query:
                params["q"] = query
            if page_token:
                params["pageToken"] = page_token
            resp = request_with_backoff(
                self._transport,
                "GET",
                f"{GMAIL_API}/users/me/messages",
                headers=self._headers(),
                params=params,
            )
            if resp.status_code >= 400:
                raise GoogleHttpError("gmail_list_failed", status_code=resp.status_code)
            payload = resp.json()
            msgs = payload.get("messages") or []
            for m in msgs:
                if isinstance(m, dict) and m.get("id"):
                    ids.append(str(m["id"]))
            page_token = str(payload.get("nextPageToken") or "") or None
            if not page_token:
                break
            if page_i == max_pages - 1:
                truncated = True
                _logger.info("gmail_list_truncated pages=%s query=%s", max_pages, query or "-")
        return ids, truncated

    def get_message(self, message_id: str) -> GmailMessage:
        resp = request_with_backoff(
            self._transport,
            "GET",
            f"{GMAIL_API}/users/me/messages/{message_id}",
            headers=self._headers(),
            params={"format": "full"},
        )
        if resp.status_code >= 400:
            raise GoogleHttpError("gmail_get_failed", status_code=resp.status_code)
        return parse_message(resp.json())

    def get_message_rfc_message_id(self, message_id: str) -> str | None:
        """Return the RFC Message-ID header for a Gmail message, or None if absent.

        Pre-send metadata only: transport/timeout and non-2xx (except 404 omit-header)
        raise ``gmail_unavailable_not_sent`` / ``invalid_grant`` — never ambiguous send.
        """
        try:
            resp = request_with_backoff(
                self._transport,
                "GET",
                f"{GMAIL_API}/users/me/messages/{message_id}",
                headers=self._headers(),
                params={"format": "metadata", "metadataHeaders": ["Message-ID"]},
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise GoogleHttpError("gmail_unavailable_not_sent") from exc
        if resp.status_code == 404:
            # Message gone or inaccessible — omit threading headers; still may send.
            return None
        if resp.status_code >= 400:
            err_code: str | None = None
            try:
                payload = resp.json()
                if isinstance(payload, dict):
                    raw_err = payload.get("error")
                    if isinstance(raw_err, str):
                        err_code = raw_err
                    elif isinstance(raw_err, dict) and isinstance(raw_err.get("status"), str):
                        err_code = str(raw_err.get("status"))
            except Exception:
                err_code = None
            if resp.status_code == 401 or err_code == "invalid_grant":
                raise GoogleHttpError("invalid_grant", status_code=resp.status_code)
            raise GoogleHttpError("gmail_unavailable_not_sent", status_code=resp.status_code)
        try:
            payload = resp.json()
        except Exception as exc:
            raise GoogleHttpError("gmail_unavailable_not_sent") from exc
        headers = (payload.get("payload") or {}).get("headers") or []
        for h in headers:
            if not isinstance(h, dict):
                continue
            if str(h.get("name") or "").lower() == "message-id":
                value = str(h.get("value") or "").strip()
                return value or None
        return None

    def history_message_ids(self, *, start_history_id: str) -> tuple[list[str], list[str], bool, str | None] | None:
        """Return (added, removed, truncated, last_processed_history_id), or None to full-resync.

        removed includes messagesDeleted plus trash / leave-INBOX / SPAM label changes.
        On truncate, last_processed_history_id is the max history record id from pages read.
        """
        added: list[str] = []
        removed: list[str] = []
        page_token: str | None = None
        max_pages = _max_pages("OPSPILOT_GMAIL_HISTORY_MAX_PAGES")
        truncated = False
        last_hid: str | None = None
        for page_i in range(max_pages):
            params: dict[str, Any] = {
                "startHistoryId": start_history_id,
                "historyTypes": ["messageAdded", "messageDeleted", "labelAdded", "labelRemoved"],
            }
            if page_token:
                params["pageToken"] = page_token
            resp = request_with_backoff(
                self._transport,
                "GET",
                f"{GMAIL_API}/users/me/history",
                headers=self._headers(),
                params=params,
            )
            # 404 = expired/unknown startHistoryId. 400 = invalid start id (post-reconnect) or
            # malformed historyTypes; both require a full list resync rather than failing sync.
            if resp.status_code in {400, 404}:
                return None
            if resp.status_code >= 400:
                raise GoogleHttpError("gmail_history_failed", status_code=resp.status_code)
            payload = resp.json()
            for entry in payload.get("history") or []:
                if not isinstance(entry, dict):
                    continue
                hid = entry.get("id")
                if hid is not None:
                    last_hid = str(hid)
                for added_entry in entry.get("messagesAdded") or []:
                    mid = _history_message_id(added_entry)
                    if mid:
                        added.append(mid)
                for deleted_entry in entry.get("messagesDeleted") or []:
                    mid = _history_message_id(deleted_entry)
                    if mid:
                        removed.append(mid)
                for lab in entry.get("labelsAdded") or []:
                    if not isinstance(lab, dict):
                        continue
                    labels = {str(x) for x in (lab.get("labelIds") or []) if x}
                    mid = _history_message_id(lab)
                    if mid and ("TRASH" in labels or "SPAM" in labels):
                        removed.append(mid)
                for lab in entry.get("labelsRemoved") or []:
                    if not isinstance(lab, dict):
                        continue
                    labels = {str(x) for x in (lab.get("labelIds") or []) if x}
                    mid = _history_message_id(lab)
                    if mid and "INBOX" in labels:
                        removed.append(mid)
            page_token = str(payload.get("nextPageToken") or "") or None
            if not page_token:
                break
            if page_i == max_pages - 1:
                truncated = True
                _logger.info(
                    "gmail_history_truncated pages=%s start=%s last_hid=%s",
                    max_pages,
                    start_history_id,
                    last_hid or "-",
                )
        return added, removed, truncated, last_hid

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
        from opspilot.services.mail_address import MailAddressError, assert_safe_subject, format_to_header
        from opspilot.services.operator_session import demo_mode_enabled
        from opspilot.services.send_allowlist import recipients_allowed

        if demo_mode_enabled():
            raise GoogleHttpError("demo_mode_blocks_send")
        if not recipients_allowed(to_addrs):
            raise GoogleHttpError("recipient_not_allowlisted")
        if not thread_id or not in_reply_to_provider_id:
            raise GoogleHttpError("missing_thread_or_provider")
        try:
            to_header = format_to_header(to_addrs)
            safe_subject = assert_safe_subject(subject)
        except MailAddressError as exc:
            raise GoogleHttpError(exc.code) from exc

        import email.message

        # Tracks whether messages.send was invoked — used for unexpected-error classification.
        self.send_post_issued = False
        try:
            rfc_message_id = self.get_message_rfc_message_id(in_reply_to_provider_id)
        except GoogleHttpError:
            raise
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise GoogleHttpError("gmail_unavailable_not_sent") from exc
        except Exception as exc:
            raise GoogleHttpError("gmail_unavailable_not_sent") from exc

        msg = email.message.EmailMessage()
        msg["To"] = to_header
        msg["Subject"] = safe_subject
        # Prefer RFC Message-ID for threading headers; never synthesize from provider id.
        if rfc_message_id:
            msg["In-Reply-To"] = rfc_message_id
            msg["References"] = rfc_message_id
        else:
            _logger.info("missing_rfc_message_id provider_id=%s", in_reply_to_provider_id)
        msg.set_content(body if isinstance(body, str) else str(body))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii").rstrip("=")

        # Once the POST is issued, delivery cannot be ruled out on timeout/5xx/opaque 2xx.
        self.send_post_issued = True
        try:
            resp = request_with_backoff(
                self._transport,
                "POST",
                f"{GMAIL_API}/users/me/messages/send",
                headers=self._headers(),
                json={"raw": raw, "threadId": thread_id},
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise GoogleHttpError("send_outcome_unknown") from exc
        except Exception as exc:
            raise GoogleHttpError("send_outcome_unknown") from exc
        if resp.status_code >= 400:
            err_code: str | None = None
            try:
                payload = resp.json()
                if isinstance(payload, dict):
                    raw_err = payload.get("error")
                    if isinstance(raw_err, str):
                        err_code = raw_err
                    elif isinstance(raw_err, dict) and isinstance(raw_err.get("status"), str):
                        err_code = str(raw_err.get("status"))
            except Exception:
                err_code = None
            if resp.status_code == 401 or err_code == "invalid_grant":
                raise GoogleHttpError("invalid_grant", status_code=resp.status_code)
            if resp.status_code in {408, 429} or resp.status_code >= 500:
                raise GoogleHttpError("send_outcome_unknown", status_code=resp.status_code)
            raise GoogleHttpError("gmail_send_failed", status_code=resp.status_code)
        try:
            body_json = resp.json()
            mid = str((body_json or {}).get("id") or "") if isinstance(body_json, dict) else ""
        except Exception as exc:
            raise GoogleHttpError("send_outcome_unknown") from exc
        if not mid:
            # 2xx without a message id — delivery may have succeeded.
            raise GoogleHttpError("send_outcome_unknown")
        return mid


def _history_message_id(entry: object) -> str | None:
    if not isinstance(entry, dict):
        return None
    msg = entry.get("message") or {}
    if isinstance(msg, dict) and msg.get("id"):
        return str(msg["id"])
    return None
