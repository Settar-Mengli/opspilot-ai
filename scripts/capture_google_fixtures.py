#!/usr/bin/env python3
"""Read-only Google fixture capture (never run in CI).

Requires OPSPILOT_CAPTURE_FIXTURES=1 and an existing operator Google credential.
Prints counts only — never prints tokens, bodies, or raw hostnames.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "google"


def _die(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def _hash_id(raw: str, prefix: str) -> str:
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _sanitize_history(payload: dict) -> dict:
    history = []
    for entry in payload.get("history") or []:
        if not isinstance(entry, dict):
            continue
        clean: dict = {"id": _hash_id(str(entry.get("id") or "0"), "fx_hid")}
        for key in ("messagesAdded", "messagesDeleted", "labelsAdded", "labelsRemoved"):
            items = entry.get(key) or []
            out_items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                msg = item.get("message") or {}
                mid = str(msg.get("id") or "")
                tid = str(msg.get("threadId") or "")
                out: dict = {
                    "message": {
                        "id": _hash_id(mid, "fx_msg") if mid else "fx_msg_missing",
                        "threadId": _hash_id(tid, "fx_thr") if tid else "fx_thr_missing",
                    }
                }
                if "labelIds" in item:
                    out["labelIds"] = [str(x) for x in (item.get("labelIds") or [])]
                out_items.append(out)
            if out_items:
                clean[key] = out_items
        history.append(clean)
    return {
        "historyId": _hash_id(str(payload.get("historyId") or "0"), "fx_hid"),
        "history": history,
        "nextPageToken": None,
    }


def _sanitize_message(payload: dict) -> dict:
    mid = str(payload.get("id") or "msg")
    tid = str(payload.get("threadId") or "thr")
    return {
        "id": _hash_id(mid, "fx_msg"),
        "threadId": _hash_id(tid, "fx_thr"),
        "labelIds": ["INBOX"],
        "snippet": "FIXTURE_BODY",
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.test"},
                {"name": "To", "value": "ops@example.test"},
                {"name": "Subject", "value": "FIXTURE_SUBJECT"},
                {"name": "Message-ID", "value": f"<{_hash_id(mid, 'fx_msg')}@example.test>"},
                {"name": "Date", "value": "Thu, 01 Oct 2026 12:00:00 +0000"},
            ],
            "body": {"data": ""},
            "parts": [{"mimeType": "text/plain", "body": {"data": "RklYVFVSRV9CT0RZ"}}],
        },
    }


def _sanitize_calendar(payload: dict) -> dict:
    items = []
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        eid = str(item.get("id") or "evt")
        items.append(
            {
                "id": _hash_id(eid, "fx_evt"),
                "status": "confirmed",
                "summary": "FIXTURE_SUBJECT",
                "description": "FIXTURE_BODY",
                "start": item.get("start") or {"dateTime": "2026-10-01T15:00:00Z"},
                "end": item.get("end") or {"dateTime": "2026-10-01T16:00:00Z"},
                "attendees": [{"email": "peer@example.test", "responseStatus": "accepted"}],
            }
        )
    sync = payload.get("nextSyncToken")
    return {
        "items": items,
        "nextPageToken": None,
        "nextSyncToken": _hash_id(str(sync), "fx_sync") if sync else None,
    }


def main() -> None:
    if os.environ.get("OPSPILOT_CAPTURE_FIXTURES", "").strip() != "1":
        _die("Refusing capture: set OPSPILOT_CAPTURE_FIXTURES=1 (never run in CI).")
    if os.environ.get("CI", "").strip() or os.environ.get("PYTEST_CURRENT_TEST", "").strip():
        _die("Refusing capture under CI or pytest (never run in CI).")

    # Local import only after gate so CI import of this file stays side-effect free.
    from opspilot.integrations.calendar_client import CalendarClient
    from opspilot.integrations.gmail_client import GmailClient
    from opspilot.integrations.google_http import HttpxTransport, refresh_access_token
    from opspilot.integrations.google_oauth import client_id, client_secret
    from opspilot.persistence.db import create_engine, create_session_factory, get_database_url
    from opspilot.persistence.repositories import oauth_credentials

    OUT.mkdir(parents=True, exist_ok=True)
    engine = create_engine(get_database_url())
    sf = create_session_factory(engine)
    with sf() as session:
        cred = oauth_credentials.get_decrypted_refresh(session, provider="google")
    if cred is None:
        _die("No Google credential available.")
    _account, refresh = cred
    tx = HttpxTransport()
    access = refresh_access_token(
        client_id=client_id(),
        client_secret=client_secret(),
        refresh_token=refresh,
        transport=tx,
    )
    gmail = GmailClient(access_token=access, transport=tx)
    history_id = gmail.profile_history_id()
    start_hid = str(max(1, int(history_id) - 1)) if history_id.isdigit() else history_id
    hist = tx.request(
        "GET",
        "https://gmail.googleapis.com/gmail/v1/users/me/history",
        headers={"Authorization": f"Bearer {access}"},
        params={
            "startHistoryId": start_hid,
            "historyTypes": ["messageAdded", "messageDeleted", "labelAdded", "labelRemoved"],
            "maxResults": 5,
        },
    )
    hist_payload = hist.json() if hist.status_code < 400 else {"history": [], "historyId": history_id}
    ids, _trunc = gmail.list_message_ids(query="in:inbox", max_results=1)
    msg_payload = {"id": "none", "threadId": "none", "payload": {"headers": []}}
    if ids:
        msg = tx.request(
            "GET",
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{ids[0]}",
            headers={"Authorization": f"Bearer {access}"},
            params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Message-ID", "Date"]},
        )
        if msg.status_code < 400:
            msg_payload = msg.json()

    from datetime import UTC, datetime, timedelta

    cal = CalendarClient(access_token=access, transport=tx)
    now = datetime.now(UTC)
    cal_result = cal.list_events(time_min=now - timedelta(days=1), time_max=now + timedelta(days=7), max_results=3)
    # Rebuild a list-shaped payload from sanitized client events for fixture write.
    cal_payload = {
        "items": [
            {
                "id": e.provider_id,
                "status": "cancelled" if e.cancelled else "confirmed",
                "summary": e.title or "FIXTURE_SUBJECT",
                "description": "FIXTURE_BODY",
                "start": {
                    "dateTime": (e.start_at or now).isoformat().replace("+00:00", "Z"),
                },
                "end": {
                    "dateTime": (e.end_at or now).isoformat().replace("+00:00", "Z"),
                },
            }
            for e in cal_result.events[:3]
        ],
        "nextSyncToken": cal_result.next_sync_token,
    }

    history_out = _sanitize_history(hist_payload if isinstance(hist_payload, dict) else {})
    message_out = _sanitize_message(msg_payload if isinstance(msg_payload, dict) else {})
    calendar_out = _sanitize_calendar(cal_payload)
    token_out = {"error": "invalid_grant", "error_description": "FIXTURE_BODY"}

    (OUT / "history.json").write_text(json.dumps(history_out, indent=2) + "\n", encoding="utf-8")
    (OUT / "message.json").write_text(json.dumps(message_out, indent=2) + "\n", encoding="utf-8")
    (OUT / "calendar.json").write_text(json.dumps(calendar_out, indent=2) + "\n", encoding="utf-8")
    (OUT / "token_error.json").write_text(json.dumps(token_out, indent=2) + "\n", encoding="utf-8")

    print(f"history_entries={len(history_out.get('history') or [])}")
    print(f"message_written={'yes' if message_out.get('id') else 'no'}")
    print(f"calendar_items={len(calendar_out.get('items') or [])}")
    print("token_error=yes")
    print("sanitize=ok")


if __name__ == "__main__":
    main()
