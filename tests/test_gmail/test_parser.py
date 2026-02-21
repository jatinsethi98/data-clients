"""Tests for Gmail parser."""

from data_clients.gmail.parser import parse_message
from data_clients.gmail.models import ParsedEmail


def _make_raw_message(body_text="Hello world", mime_type="text/plain"):
    import base64
    encoded = base64.urlsafe_b64encode(body_text.encode()).decode()
    return {
        "id": "msg123",
        "threadId": "thread456",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "mimeType": mime_type,
            "headers": [
                {"name": "From", "value": "Alice <alice@example.com>"},
                {"name": "To", "value": "bob@example.com"},
                {"name": "Subject", "value": "Test Subject"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
            ],
            "body": {"data": encoded},
        },
    }


def test_parse_plain_message():
    raw = _make_raw_message("Hello world")
    result = parse_message(raw)
    assert isinstance(result, ParsedEmail)
    assert result.gmail_message_id == "msg123"
    assert result.sender_name == "Alice"
    assert result.sender_email == "alice@example.com"
    assert result.subject == "Test Subject"
    assert "Hello world" in result.body_text
    assert result.is_read is False  # UNREAD in labels


def test_parse_truncates_body():
    raw = _make_raw_message("x" * 20000)
    result = parse_message(raw, max_body_length=100)
    assert len(result.body_text) == 100


def test_parse_missing_headers():
    raw = {
        "id": "msg789",
        "threadId": "thread000",
        "labelIds": [],
        "payload": {
            "mimeType": "text/plain",
            "headers": [],
            "body": {"data": ""},
        },
    }
    result = parse_message(raw)
    assert result.subject == "(no subject)"
    assert result.is_read is True
