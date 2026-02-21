"""Google Calendar API client with sync and async interfaces."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from data_clients.exceptions import CalendarError

logger = logging.getLogger(__name__)


class CalendarClient:
    """Google Calendar API client with sync and async methods.

    Args:
        credentials: A google.oauth2.credentials.Credentials object.
    """

    def __init__(self, credentials):
        try:
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError(
                "google-api-python-client is required for CalendarClient. "
                "Install with: pip install data-clients[calendar]"
            )
        self._service = build("calendar", "v3", credentials=credentials)

    # ---- Sync methods ----

    def list_events(
        self,
        time_min: str | None = None,
        time_max: str | None = None,
        query: str | None = None,
        max_results: int = 10,
        calendar_id: str = "primary",
    ) -> list[dict]:
        """List calendar events in a time range."""
        try:
            kwargs: dict[str, Any] = {
                "calendarId": calendar_id,
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if time_min:
                kwargs["timeMin"] = time_min
            if time_max:
                kwargs["timeMax"] = time_max
            if query:
                kwargs["q"] = query

            result = self._service.events().list(**kwargs).execute()
            events = result.get("items", [])

            return [
                {
                    "id": event.get("id"),
                    "summary": event.get("summary", "(No title)"),
                    "description": event.get("description", ""),
                    "start": event.get("start", {}).get(
                        "dateTime", event.get("start", {}).get("date")
                    ),
                    "end": event.get("end", {}).get(
                        "dateTime", event.get("end", {}).get("date")
                    ),
                    "location": event.get("location"),
                    "attendees": [
                        a.get("email") for a in event.get("attendees", [])
                    ],
                    "status": event.get("status"),
                }
                for event in events
            ]
        except Exception as e:
            raise CalendarError(f"Failed to list events: {e}") from e

    def get_event(self, event_id: str, calendar_id: str = "primary") -> dict:
        """Get a single calendar event by ID."""
        try:
            event = (
                self._service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )
            return {
                "id": event.get("id"),
                "summary": event.get("summary", "(No title)"),
                "description": event.get("description", ""),
                "start": event.get("start", {}).get(
                    "dateTime", event.get("start", {}).get("date")
                ),
                "end": event.get("end", {}).get(
                    "dateTime", event.get("end", {}).get("date")
                ),
                "location": event.get("location"),
                "attendees": [
                    {"email": a.get("email"), "response": a.get("responseStatus")}
                    for a in event.get("attendees", [])
                ],
                "status": event.get("status"),
                "creator": event.get("creator", {}).get("email"),
                "organizer": event.get("organizer", {}).get("email"),
                "html_link": event.get("htmlLink"),
                "recurring_event_id": event.get("recurringEventId"),
            }
        except Exception as e:
            raise CalendarError(f"Failed to get event {event_id}: {e}") from e

    def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        calendar_id: str = "primary",
    ) -> dict:
        """Create a new calendar event."""
        try:
            event_body: dict[str, Any] = {
                "summary": summary,
                "start": {"dateTime": start},
                "end": {"dateTime": end},
            }
            if description:
                event_body["description"] = description
            if location:
                event_body["location"] = location
            if attendees:
                event_body["attendees"] = [{"email": email} for email in attendees]

            event = (
                self._service.events()
                .insert(calendarId=calendar_id, body=event_body)
                .execute()
            )
            return {
                "id": event.get("id"),
                "summary": event.get("summary"),
                "start": event.get("start", {}).get("dateTime"),
                "end": event.get("end", {}).get("dateTime"),
                "html_link": event.get("htmlLink"),
            }
        except Exception as e:
            raise CalendarError(f"Failed to create event: {e}") from e

    def modify_event(
        self,
        event_id: str,
        updates: dict[str, Any],
        calendar_id: str = "primary",
    ) -> dict:
        """Modify an existing calendar event.

        Args:
            event_id: The event to modify.
            updates: Dict with optional keys: summary, description, start_time,
                     end_time, location, attendees.
            calendar_id: Calendar to use.
        """
        try:
            existing = (
                self._service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )

            if "summary" in updates:
                existing["summary"] = updates["summary"]
            if "description" in updates:
                existing["description"] = updates["description"]
            if "start_time" in updates:
                existing["start"] = {"dateTime": updates["start_time"]}
            if "end_time" in updates:
                existing["end"] = {"dateTime": updates["end_time"]}
            if "location" in updates:
                existing["location"] = updates["location"]
            if "attendees" in updates:
                existing["attendees"] = [
                    {"email": email} for email in updates["attendees"]
                ]

            updated = (
                self._service.events()
                .update(calendarId=calendar_id, eventId=event_id, body=existing)
                .execute()
            )
            return {
                "id": updated.get("id"),
                "summary": updated.get("summary"),
                "start": updated.get("start", {}).get("dateTime"),
                "end": updated.get("end", {}).get("dateTime"),
            }
        except Exception as e:
            raise CalendarError(f"Failed to modify event {event_id}: {e}") from e

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        """Delete a calendar event."""
        try:
            self._service.events().delete(
                calendarId=calendar_id, eventId=event_id
            ).execute()
        except Exception as e:
            raise CalendarError(f"Failed to delete event {event_id}: {e}") from e

    # ---- Async wrappers (asyncio.to_thread) ----

    async def alist_events(self, **kwargs) -> list[dict]:
        """Async version of list_events."""
        return await asyncio.to_thread(self.list_events, **kwargs)

    async def aget_event(self, event_id: str, calendar_id: str = "primary") -> dict:
        """Async version of get_event."""
        return await asyncio.to_thread(self.get_event, event_id, calendar_id)

    async def acreate_event(self, **kwargs) -> dict:
        """Async version of create_event."""
        return await asyncio.to_thread(self.create_event, **kwargs)

    async def amodify_event(
        self, event_id: str, updates: dict[str, Any], calendar_id: str = "primary"
    ) -> dict:
        """Async version of modify_event."""
        return await asyncio.to_thread(
            self.modify_event, event_id, updates, calendar_id
        )

    async def adelete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        """Async version of delete_event."""
        return await asyncio.to_thread(self.delete_event, event_id, calendar_id)
