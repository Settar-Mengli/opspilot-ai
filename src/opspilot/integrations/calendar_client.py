"""Google Calendar readonly client (syncToken + time window)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from opspilot.integrations.google_http import GoogleHttpError, GoogleTransport

CAL_API = "https://www.googleapis.com/calendar/v3"


@dataclass(frozen=True)
class CalendarEvent:
    provider_id: str
    title: str
    start_at: datetime | None
    end_at: datetime | None
    cancelled: bool = False


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
        page_token: str | None = None,
        max_results: int | None = None,
    ) -> tuple[list[CalendarEvent], str | None]:
        """Return (events, next_sync_token). next_sync_token None + empty means 410 → full resync.

        With ``syncToken``, only that token is sent (+ optional pageToken/maxResults).
        Google forbids combining syncToken with showDeleted=false / timeMin / timeMax / orderBy.
        """
        params: dict[str, Any] = {}
        if sync_token:
            params["syncToken"] = sync_token
        else:
            # Full sync: time window only (never combine these with syncToken).
            params["singleEvents"] = "true"
            params["showDeleted"] = "false"
            params["timeMin"] = time_min.astimezone(UTC).isoformat().replace("+00:00", "Z")
            params["timeMax"] = time_max.astimezone(UTC).isoformat().replace("+00:00", "Z")
        if page_token:
            params["pageToken"] = page_token
        if max_results is not None:
            params["maxResults"] = max_results
        resp = self._transport.request(
            "GET",
            f"{CAL_API}/calendars/primary/events",
            headers=self._headers(),
            params=params,
        )
        if resp.status_code == 410:
            return [], None
        if resp.status_code >= 400:
            raise GoogleHttpError("calendar_list_failed", status_code=resp.status_code)
        payload = resp.json()
        events: list[CalendarEvent] = []
        for item in payload.get("items") or []:
            if isinstance(item, dict):
                parsed = parse_event(item)
                if parsed is not None:
                    events.append(parsed)
        next_token = payload.get("nextSyncToken")
        return events, str(next_token) if next_token else sync_token
