"""Tests for calendar client."""

from unittest.mock import MagicMock, patch

import pytest

from data_clients.calendar.client import CalendarClient
from data_clients.exceptions import CalendarError


@pytest.fixture
def calendar_client():
    mock_service = MagicMock()
    creds = MagicMock()
    with patch("googleapiclient.discovery.build", return_value=mock_service):
        client = CalendarClient(creds)
    return client, mock_service


def test_list_events(calendar_client):
    client, service = calendar_client
    service.events().list().execute.return_value = {
        "items": [
            {
                "id": "evt1",
                "summary": "Team Meeting",
                "start": {"dateTime": "2024-01-15T09:00:00-05:00"},
                "end": {"dateTime": "2024-01-15T10:00:00-05:00"},
                "status": "confirmed",
            }
        ]
    }
    events = client.list_events()
    assert len(events) == 1
    assert events[0]["summary"] == "Team Meeting"


def test_create_event(calendar_client):
    client, service = calendar_client
    service.events().insert().execute.return_value = {
        "id": "new-evt",
        "summary": "Lunch",
        "start": {"dateTime": "2024-01-15T12:00:00"},
        "end": {"dateTime": "2024-01-15T13:00:00"},
        "htmlLink": "https://calendar.google.com/event?id=new-evt",
    }
    result = client.create_event(
        summary="Lunch",
        start="2024-01-15T12:00:00",
        end="2024-01-15T13:00:00",
    )
    assert result["id"] == "new-evt"


def test_delete_event(calendar_client):
    client, service = calendar_client
    service.events().delete().execute.return_value = None
    client.delete_event("evt1")


def test_list_events_error(calendar_client):
    client, service = calendar_client
    service.events().list().execute.side_effect = Exception("API error")
    with pytest.raises(CalendarError, match="Failed to list events"):
        client.list_events()
