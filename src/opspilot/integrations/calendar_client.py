"""Google Calendar readonly client (syncToken + time window)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from opspilot.integrations.google_http import GoogleHttpError, GoogleTransport, request_with_backoff

CAL_API = "https://www.googleapis.com/calendar/v3"
_logger = logging.getLogger("opspilot.sync.calendar")


def _max_pages(env_name: str, default: int = 20) -> int:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


@dataclass(frozen=True)
class CalendarEvent:
    provider_id: str
    title: str
    start_at: datetime | None
    end_at: datetime | None
    cancelled: bool = False


@dataclass(frozen=True)
class CalendarListResult:
    events: list[CalendarEvent]
    next_sync_token: str | None
    truncated: bool
    gone: bool = False  # 410 syncToken expired


def _parse_dt(value: dict[str, Any] | None) -> datetime | None:
    if not value or not isinstance(value, dict):
        return None
    raw = value.get("dateTime") or value.get("date")
    if not raw:
        return None
    text = str(raw)
    if len(text) == 10:
        return datetime.fromisoformat(text).replace(tzinfo=UTC)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def parse_event(raw: dict[str, Any]) -> CalendarEvent | None:
    provider_id = str(raw.get("id") or "")
    if not provider_id:
        return None
    if str(raw.get("status") or "").lower() == "cancelled":
        return CalendarEvent(
            provider_id=provider_id,
            title=str(raw.get("summary") or ""),
            start_at=None,
            end_at=None,
            cancelled=True,
        )
    start = _parse_dt(raw.get("start") if isinstance(raw.get("start"), dict) else None)
    end = _parse_dt(raw.get("end") if isinstance(raw.get("end"), dict) else None)
    if start is None or end is None:
        return None
    title = str(raw.get("summary") or "(no title)")
    return CalendarEvent(
        provider_id=provider_id,
        title=title,
        start_at=start,
        end_at=end,
        cancelled=False,
    )


class CalendarClient:
    def __init__(self, *, access_token: str, transport: GoogleTransport) -> None:
        self._token = access_token
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def list_events(
        self,
        *,
        time_min: datetime,
        time_max: datetime,
        sync_token: str | None = None,
        max_results: int | None = None,
    ) -> CalendarListResult:
        """Paginate events. next_sync_token only set when the final page is reached (not truncated).

        With ``syncToken``, only that token is sent (+ optional pageToken/maxResults).
        Google forbids combining syncToken with showDeleted=false / timeMin / timeMax / orderBy.
        """
        events: list[CalendarEvent] = []
        page_token: str | None = None
        max_pages = _max_pages("OPSPILOT_CALENDAR_LIST_MAX_PAGES")
        truncated = False
        next_sync: str | None = None
        for page_i in range(max_pages):
            params: dict[str, Any] = {}
            if sync_token:
                params["syncToken"] = sync_token
            else:
                params["singleEvents"] = "true"
                params["showDeleted"] = "true"
                params["timeMin"] = time_min.astimezone(UTC).isoformat().replace("+00:00", "Z")
                params["timeMax"] = time_max.astimezone(UTC).isoformat().replace("+00:00", "Z")
            if page_token:
                params["pageToken"] = page_token
            if max_results is not None:
                params["maxResults"] = max_results
            resp = request_with_backoff(
                self._transport,
                "GET",
                f"{CAL_API}/calendars/primary/events",
                headers=self._headers(),
                params=params,
            )
            if resp.status_code == 410:
                return CalendarListResult(events=[], next_sync_token=None, truncated=False, gone=True)
            if resp.status_code >= 400:
                raise GoogleHttpError("calendar_list_failed", status_code=resp.status_code)
            payload = resp.json()
            for item in payload.get("items") or []:
                if isinstance(item, dict):
                    parsed = parse_event(item)
                    if parsed is not None:
                        events.append(parsed)
            page_token = str(payload.get("nextPageToken") or "") or None
            raw_sync = payload.get("nextSyncToken")
            if raw_sync:
                next_sync = str(raw_sync)
            if not page_token:
                break
            if page_i == max_pages - 1:
                truncated = True
                _logger.info("calendar_list_truncated pages=%s", max_pages)
                next_sync = None  # never store syncToken mid-pagination
        if truncated:
            next_sync = None
        elif next_sync is None and sync_token and not truncated:
            # Unchanged token when API omits nextSyncToken on empty delta.
            next_sync = sync_token
        return CalendarListResult(
            events=events,
            next_sync_token=next_sync,
            truncated=truncated,
            gone=False,
        )
